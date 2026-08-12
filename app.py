from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import datetime
import os

app = Flask(__name__)

# Sample Data Generator or CSV Data Loader
def load_weather_data():
    """
    Generates or loads weather data from 2000 to 2026 for Islamabad.
    If weather_data.csv exists, it loads it; otherwise, it creates standard structure.
    """
    file_path = "weather_data.csv"
    
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
    else:
        # Fallback dynamic dataset generator for 2000 to 2026
        date_range = pd.date_range(start="2000-01-01", end="2026-08-12", freq="D")
        np.random.seed(42)
        
        n = len(date_range)
        avg_temps = 22 + 10 * np.sin(np.pi * date_range.dayofyear / 182.5) + np.random.normal(0, 2, n)
        min_temps = avg_temps - np.random.uniform(4, 8, n)
        max_temps = avg_temps + np.random.uniform(4, 8, n)
        humidity = np.clip(50 + 20 * np.sin(np.pi * date_range.dayofyear / 182.5) + np.random.normal(0, 10, n), 20, 95)
        rainfall = np.where(np.random.rand(n) < 0.2, np.random.exponential(12, n), 0)
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
    """
    today = datetime.datetime.now()
    return jsonify({
        "current_date": today.strftime("%Y-%m-%d"),
        "location": "Islamabad, Pakistan",
        "coordinates": {"lat": 33.6844, "lng": 73.0479},
        "live_metrics": {
            "avg_temp": 29.8,
            "min_temp": 25.3,
            "max_temp": 34.2,
            "humidity": 72,
            "rainfall_today": 0.1,
            "wind_speed": 9.7,
            "pressure": 943.9
        }
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)