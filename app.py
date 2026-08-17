from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import datetime
import os
import math

app = Flask(__name__)

ISB_LAT, ISB_LNG = 33.6844, 73.0479


def _day_rng(*parts):
    """Deterministic RNG seeded from date/hour parts, so a given day/hour
    always returns the same synthetic reading (instead of re-randomizing
    on every request), while still changing from one day/hour to the next."""
    seed = abs(hash(("islamabad-climate",) + parts)) % (2 ** 32)
    return np.random.RandomState(seed)


# ---------------------------------------------------------------------------
# CLIMATOLOGY — built from the actual historical dataset (weather_data.csv,
# or the generated fallback), instead of a hand-picked sine curve. Every
# forecast below (today's reading, the 7-day outlook, the 10-day heatwave
# outlook) is anchored to what the real data says is "normal" for that
# day-of-year, with a small deterministic day-to-day variation layered on
# top so the numbers still move sensibly instead of jumping randomly.
# ---------------------------------------------------------------------------
_climatology_cache = None


def build_climatology(df):
    d = df.copy()
    d["Date_dt"] = pd.to_datetime(d["Date_Str"])
    d["doy"] = d["Date_dt"].dt.dayofyear

    clim = {}
    for doy in range(1, 367):
        # +/- 5 day circular window around this day-of-year, pooled across
        # all historical years, so each estimate rests on enough samples.
        window = {((doy + off - 1) % 366) + 1 for off in range(-5, 6)}
        subset = d[d["doy"].isin(window)]
        if subset.empty:
            continue
        clim[doy] = {
            "max_mean": float(subset["Max Temp (°C)"].mean()),
            "max_std": float(subset["Max Temp (°C)"].std(ddof=0) or 3.0),
            "min_mean": float(subset["Min Temp (°C)"].mean()),
            "min_std": float(subset["Min Temp (°C)"].std(ddof=0) or 3.0),
            "humidity_mean": float(subset["Relative Humidity (%)"].mean()),
            "humidity_std": float(subset["Relative Humidity (%)"].std(ddof=0) or 8.0),
            "wind_mean": float(subset["Max Wind Speed (km/h)"].mean()),
            "pressure_mean": float(subset["Pressure (hPa)"].mean()),
            "rain_prob": float((subset["Rainfall (mm)"] > 0).mean()),
        }
    return clim


def get_climatology():
    global _climatology_cache
    if _climatology_cache is None:
        _climatology_cache = build_climatology(load_weather_data())
    return _climatology_cache


def _climatology_for_doy(doy):
    clim = get_climatology()
    if doy in clim:
        return clim[doy]
    nearest = min(clim.keys(), key=lambda k: abs(k - doy))
    return clim[nearest]


def seasonal_stats(date_obj):
    """Forecast for a given calendar date, built from the dataset's own
    day-of-year climatology (mean/std of real historical readings) plus a
    small deterministic day-to-day variation, rather than an arbitrary
    formula unrelated to the data."""
    doy = date_obj.timetuple().tm_yday
    c = _climatology_for_doy(doy)
    rng = _day_rng("day", date_obj.isoformat())

    max_temp = round(c["max_mean"] + rng.normal(0, c["max_std"] * 0.5), 1)
    min_temp = round(c["min_mean"] + rng.normal(0, c["min_std"] * 0.5), 1)
    if min_temp > max_temp - 2:
        min_temp = round(max_temp - 2, 1)
    avg_temp = round((max_temp + min_temp) / 2, 1)

    humidity = float(np.clip(c["humidity_mean"] + rng.normal(0, c["humidity_std"] * 0.5), 15, 98))
    wind_speed = round(max(2.0, c["wind_mean"] + rng.normal(0, 2)), 1)
    pressure = round(c["pressure_mean"] + rng.normal(0, 2), 1)

    rain_chance = float(np.clip(c["rain_prob"] * 100 + rng.normal(0, 12), 0, 100))
    rainfall_mm = round(float(rng.exponential(9)), 1) if rain_chance > 45 else 0.0

    return {
        "min_temp": min_temp, "max_temp": max_temp,
        "avg_temp": avg_temp, "humidity": round(humidity, 1),
        "rain_chance": round(rain_chance, 1), "rainfall_mm": rainfall_mm,
        "wind_speed": wind_speed, "pressure": pressure,
        "normal_max": round(c["max_mean"], 1),   # dataset climatological normal, for departure-from-normal calcs
    }


def diurnal_temp(date_obj, hour, day_stats):
    """Interpolate an hourly temp from the day's min/max using a realistic
    diurnal curve (coolest ~05:00, warmest ~15:00)."""
    phase = (hour - 5) / 24 * 2 * math.pi
    factor = (1 - math.cos(phase)) / 2  # 0 at 05:00, 1 at 17:00
    rng = _day_rng("hour", date_obj.isoformat(), hour)
    return round(day_stats["min_temp"] + (day_stats["max_temp"] - day_stats["min_temp"]) * factor + rng.normal(0, 0.4), 1)


def hourly_rain_chance(date_obj, hour, day_stats):
    rng = _day_rng("hour-rain", date_obj.isoformat(), hour)
    return round(float(np.clip(day_stats["rain_chance"] + rng.normal(0, 12), 0, 100)), 1)


def condition_for(rain_chance, hour):
    is_day = 6 <= hour < 19
    if rain_chance > 65:
        return "thunderstorm", "⛈️"
    if rain_chance > 35:
        return "rain", "🌧️"
    if rain_chance > 18:
        return "cloudy", "☁️"
    if rain_chance > 8:
        return "partly-cloudy", ("⛅" if is_day else "☁️")
    return ("clear-day", "☀️") if is_day else ("clear-night", "🌙")


# ---------------------------------------------------------------------------
# HEAT INDEX — official NWS Rothfusz regression (the exact 9-term equation:
# HI = c1 + c2*T + c3*R + c4*T*R + c5*T² + c6*R² + c7*T²*R + c8*T*R² + c9*T²*R²),
# including the NWS's own simple-formula fallback below 80°F and the low/high
# humidity adjustments. Source: NOAA/NWS Technical Attachment SR 90-23.
# https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
# ---------------------------------------------------------------------------
def heat_index_c(temp_c, humidity):
    T = temp_c * 9 / 5 + 32  # NWS formula is defined in °F
    R = humidity

    hi_simple = 0.5 * (T + 61 + ((T - 68) * 1.2) + (R * 0.094))

    if (hi_simple + T) / 2 < 80:
        hi_f = hi_simple
    else:
        hi_f = (
            -42.379 + 2.04901523 * T + 10.14333127 * R
            - 0.22475541 * T * R - 0.00683783 * T * T
            - 0.05481717 * R * R + 0.00122874 * T * T * R
            + 0.00085282 * T * R * R - 0.00000199 * T * T * R * R
        )
        if R < 13 and 80 <= T <= 112:
            hi_f -= ((13 - R) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
        elif R > 85 and 80 <= T <= 87:
            hi_f += ((R - 85) / 10) * ((87 - T) / 5)

    return (hi_f - 32) * 5 / 9  # back to °C


# ---------------------------------------------------------------------------
# HEATWAVE CLASSIFICATION — Pakistan Meteorological Department / NDMA
# criteria: a heatwave is max temperature reaching 40°C (plains, which
# Islamabad's PMD advisories are issued under) WITH a departure of 4.5–6.4°C
# above the normal for that day; severe heatwave is >=45°C or a >=6.5°C
# departure. (NDMA Heatwave Guidelines 2025; PMD/WMO departure-from-normal
# definition.) A heat-index based "Heat Advisory" tier is added below the
# formal heatwave threshold as an early-warning signal.
# ---------------------------------------------------------------------------
def classify_heat_risk(max_temp, heat_index, departure):
    if max_temp >= 45 or departure >= 6.5:
        return "SEVERE HEATWAVE"
    if max_temp >= 40 and departure >= 4.5:
        return "HEATWAVE"
    # Below the official PMD threshold: a warm/humid precursor signal, not a heatwave
    if max_temp >= 37 or departure >= 2.5 or heat_index >= 41:
        return "HEAT ADVISORY"
    return "NORMAL"


# Sample Data Generator or CSV Data Loader
def load_weather_data():
    """
    Loads real historical weather data if a CSV is present, otherwise falls
    back to a generated dataset.

    Looks for, in order:
      1. weather_data.csv (the app's expected filename)
      2. islamabad_weather_2000_2026_with_humidity.csv (fetch_data.py's
         Open-Meteo Archive API output — real ERA5 reanalysis data)
    Either file is normalized to the columns the rest of the app expects
    (Date_Str, Year, Month + the existing metric columns), regardless of
    whether the source file already has Date_Str/Year/Month or just a
    single "Date" column.
    """
    candidates = ["weather_data.csv", "islamabad_weather_2000_2026_with_humidity.csv"]
    file_path = next((p for p in candidates if os.path.exists(p)), None)

    if file_path:
        df = pd.read_csv(file_path)

        # Real fetch_data.py output uses "Date"; normalize to "Date_Str"
        if "Date_Str" not in df.columns and "Date" in df.columns:
            df = df.rename(columns={"Date": "Date_Str"})

        # Derive Year/Month if the source CSV doesn't already have them
        if "Year" not in df.columns or "Month" not in df.columns:
            date_dt = pd.to_datetime(df["Date_Str"])
            df["Year"] = date_dt.dt.year
            df["Month"] = date_dt.dt.strftime("%m")

        # Open-Meteo's daily precipitation/humidity can carry NaNs on rare
        # missing-data days; fill so downstream stats/climatology don't break
        numeric_cols = [
            "Avg Temp (°C)", "Min Temp (°C)", "Max Temp (°C)",
            "Relative Humidity (%)", "Rainfall (mm)",
            "Max Wind Speed (km/h)", "Pressure (hPa)"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].interpolate().ffill().bfill()
    else:
        # Fallback dynamic dataset generator, always running up to the current date
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        date_range = pd.date_range(start="2000-01-01", end=today_str, freq="D")
        np.random.seed(42)
        
        n = len(date_range)
        seasonal_phase = np.cos(2 * np.pi * (date_range.dayofyear - 172) / 365)
        avg_temps = 23 + 14 * seasonal_phase + np.random.normal(0, 2, n)
        min_temps = avg_temps - np.random.uniform(4, 8, n)
        max_temps = avg_temps + np.random.uniform(4, 8, n)
        humidity = np.clip(55 - 15 * seasonal_phase + np.random.normal(0, 10, n), 20, 95)
        # Monsoon bump (Jul-Aug) makes rain more likely, matching Islamabad's real pattern
        monsoon_mask = date_range.month.isin([7, 8])
        rain_prob = np.where(monsoon_mask, 0.45, 0.2)
        rainfall = np.where(np.random.rand(n) < rain_prob, np.random.exponential(12, n), 0)
        wind_speed = np.random.uniform(5, 25, n)
        pressure = np.random.uniform(1005, 1020, n)
        
        df = pd.DataFrame({
            "Date_Str": date_range.strftime("%Y-%m-%d"),
            "Year": date_range.year,
            "Month": date_range.strftime("%m"),
            "Avg Temp (°C)": np.round(avg_temps, 1),
            "Min Temp (°C)": np.round(min_temps, 1),
            "Max Temp (°C)": np.round(max_temps, 1),
            "Relative Humidity (%)": np.round(humidity, 1),
            "Rainfall (mm)": np.round(rainfall, 1),
            "Max Wind Speed (km/h)": np.round(wind_speed, 1),
            "Pressure (hPa)": np.round(pressure, 1)
        })
    
    return df

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/weather-data", methods=["GET"])
def get_weather_data():
    """
    API endpoint returning all daily climate records for Page 2 comparisons & table rendering.
    """
    df = load_weather_data()
    return jsonify({
        "status": "success",
        "total_records": len(df),
        "records": df.to_dict(orient="records")
    })

@app.route("/api/current-status", methods=["GET"])
def get_current_status():
    """
    Returns real-time current date sync & live spatial metrics for Page 1.
    Values now come from the seasonal model for TODAY's actual date/hour,
    instead of a fixed sample reading.
    """
    now = datetime.datetime.now()
    day_stats = seasonal_stats(now.date())
    hour = now.hour
    current_temp = diurnal_temp(now.date(), hour, day_stats)
    rain_chance = hourly_rain_chance(now.date(), hour, day_stats)
    condition, icon = condition_for(rain_chance, hour)

    return jsonify({
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "location": "Islamabad, Pakistan",
        "coordinates": {"lat": ISB_LAT, "lng": ISB_LNG},
        "condition": condition,
        "icon": icon,
        "is_day": 6 <= hour < 19,
        "live_metrics": {
            "avg_temp": current_temp,
            "min_temp": day_stats["min_temp"],
            "max_temp": day_stats["max_temp"],
            "humidity": day_stats["humidity"],
            "rainfall_today": day_stats["rainfall_mm"],
            "rain_chance": rain_chance,
            "wind_speed": day_stats["wind_speed"],
            "pressure": day_stats["pressure"]
        }
    })


@app.route("/api/live-forecast", methods=["GET"])
def get_live_forecast():
    """
    Returns a forecast that always starts from the real current date/hour:
    - next 24 hours (temp, rain chance, condition/icon)
    - next 7 days (min/max temp, rainfall, condition/icon)
    - spatial micro-site estimates (urban core / hills) derived from today's average
    Everything is deterministic per date/hour, so it's stable within a session
    but genuinely moves forward as the real date advances.
    """
    now = datetime.datetime.now()
    today = now.date()
    today_stats = seasonal_stats(today)

    hourly = []
    for i in range(24):
        future = now + datetime.timedelta(hours=i)
        d = future.date()
        stats = seasonal_stats(d) if d != today else today_stats
        temp = diurnal_temp(d, future.hour, stats)
        rain_chance = hourly_rain_chance(d, future.hour, stats)
        condition, icon = condition_for(rain_chance, future.hour)
        hourly.append({
            "time": future.strftime("%H:00"),
            "date": d.isoformat(),
            "temp": temp,
            "rain_chance": rain_chance,
            "condition": condition,
            "icon": icon
        })

    daily = []
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        stats = seasonal_stats(d)
        # midday condition is representative for the day's icon
        condition, icon = condition_for(stats["rain_chance"], 15)
        daily.append({
            "date": d.isoformat(),
            "label": "Today" if i == 0 else d.strftime("%a"),
            "min_temp": stats["min_temp"],
            "max_temp": stats["max_temp"],
            "rain_chance": stats["rain_chance"],
            "rainfall_mm": stats["rainfall_mm"],
            "condition": condition,
            "icon": icon
        })

    current_temp = diurnal_temp(today, now.hour, today_stats)
    current_condition, current_icon = condition_for(
        hourly_rain_chance(today, now.hour, today_stats), now.hour
    )

    spatial = {
        "avg": current_temp,
        "high": round(current_temp + 4.4, 1),   # urban core / Blue Area heat-island effect
        "low": round(current_temp - 3.7, 1),    # Margalla foothills, Pir Sohawa
    }

    return jsonify({
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "is_day": 6 <= now.hour < 19,
        "current": {
            "temp": current_temp,
            "humidity": today_stats["humidity"],
            "wind_speed": today_stats["wind_speed"],
            "pressure": today_stats["pressure"],
            "rainfall_today": today_stats["rainfall_mm"],
            "condition": current_condition,
            "icon": current_icon
        },
        "spatial": spatial,
        "hourly": hourly,
        "daily": daily
    })


@app.route("/api/heatwave-forecast", methods=["GET"])
def get_heatwave_forecast():
    """
    Forward-looking heatwave prediction for the next 10 days, starting from
    the real current date. Built on the dataset's own day-of-year climatology
    (not an arbitrary formula), using the official NWS Rothfusz heat-index
    equation and PMD/NDMA heatwave criteria (40°C + 4.5-6.4°C departure from
    normal = Heatwave; >=45°C or >=6.5°C departure = Severe Heatwave).
    """
    today = datetime.date.today()
    OUTLOOK_DAYS = 10

    days = []
    for i in range(OUTLOOK_DAYS):
        d = today + datetime.timedelta(days=i)
        stats = seasonal_stats(d)
        hi = heat_index_c(stats["max_temp"], stats["humidity"])
        departure = round(stats["max_temp"] - stats["normal_max"], 1)
        risk = classify_heat_risk(stats["max_temp"], hi, departure)
        days.append({
            "date": d.isoformat(),
            "label": "Today" if i == 0 else d.strftime("%a %d"),
            "max_temp": stats["max_temp"],
            "min_temp": stats["min_temp"],
            "humidity": stats["humidity"],
            "heat_index": round(hi, 1),
            "normal_max": stats["normal_max"],
            "departure": departure,
            "risk": risk
        })

    consecutive = 0
    for day in days:
        if day["risk"] in ("HEATWAVE", "SEVERE HEATWAVE"):
            consecutive += 1
        else:
            break

    peak_day = max(days, key=lambda d: d["max_temp"])

    order = {"NORMAL": 0, "HEAT ADVISORY": 1, "HEATWAVE": 2, "SEVERE HEATWAVE": 3}
    near_term = days[:5]  # near-term days weigh more heavily on the overall outlook
    overall_risk = max(near_term, key=lambda d: order[d["risk"]])["risk"]

    base_score = {"NORMAL": 15, "HEAT ADVISORY": 42, "HEATWAVE": 75, "SEVERE HEATWAVE": 97}[overall_risk]
    risk_score = min(100, base_score + consecutive * 2)

    advisories = {
        "NORMAL": "No heatwave signal in the outlook window — temperatures are tracking close to the seasonal normal.",
        "HEAT ADVISORY": "Temperatures trending above normal. Stay hydrated during midday hours and limit strenuous outdoor activity between 12–4 PM.",
        "HEATWAVE": "PMD heatwave criteria met (max temp ≥40°C with a 4.5°C+ departure from the seasonal normal for this date). Vulnerable groups should avoid peak-hour exposure. Elevated forest-fire risk in the Margalla Hills.",
        "SEVERE HEATWAVE": "Severe heatwave criteria met (≥45°C or 6.5°C+ departure from normal). Recommended: hydration stations, reduced outdoor labor hours, and a high wildfire alert for the Margalla Range."
    }

    return jsonify({
        "current_date": today.isoformat(),
        "outlook_days": OUTLOOK_DAYS,
        "daily": days,
        "consecutive_high_risk_days": consecutive,
        "peak_day": peak_day,
        "overall_risk": overall_risk,
        "risk_score": risk_score,
        "advisory": advisories[overall_risk],
        "criteria_note": "Based on PMD/NDMA heatwave criteria (40°C plains threshold + departure-from-normal) and the NWS Rothfusz heat-index equation."
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)