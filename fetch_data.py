import pandas as pd
import requests

# Islamabad Coordinates
LAT = 33.6844
LON = 73.0479

START_DATE = "2000-01-01"
END_DATE = "2026-08-10"

# Open-Meteo Archive API URL
url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "daily": [
        "temperature_2m_mean",
        "temperature_2m_min",
        "temperature_2m_max",
        "relative_humidity_2m_mean",  # Humidity Included!
        "precipitation_sum",
        "wind_speed_10m_max",
        "surface_pressure_mean",
    ],
    "timezone": "Asia/Karachi",
}

print(
    "Fetching weather data with Humidity for Islamabad (2000 - 2026) via Open-Meteo..."
)
response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    daily_data = data.get("daily", {})

    df = pd.DataFrame(daily_data)

    # Rename columns for clarity
    column_mapping = {
        "time": "Date",
        "temperature_2m_mean": "Avg Temp (°C)",
        "temperature_2m_min": "Min Temp (°C)",
        "temperature_2m_max": "Max Temp (°C)",
        "relative_humidity_2m_mean": "Relative Humidity (%)",
        "precipitation_sum": "Rainfall (mm)",
        "wind_speed_10m_max": "Max Wind Speed (km/h)",
        "surface_pressure_mean": "Pressure (hPa)",
    }

    df = df.rename(columns=column_mapping)

    # Save to CSV
    csv_filename = "islamabad_weather_2000_2026_with_humidity.csv"
    df.to_csv(csv_filename, index=False)

    print(
        f"✅ SUCCESS! Fetched {len(df)} days of data including Humidity.\nSaved to '{csv_filename}'."
    )
    print("\n--- Data Preview ---")
    print(df.head())
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)