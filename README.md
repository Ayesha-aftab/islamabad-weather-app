# 🌡️ Islamabad Climate Forecasting & Heatwave Risk Assessment Dashboard

An interactive climate analysis and temperature forecasting dashboard developed for **Islamabad, Pakistan**. The project uses historical climate data and a **statistical time-series forecasting approach** to analyze temperature and humidity patterns, generate future temperature forecasts, and assess potential heatwave/temperature risk.

> **Note:** This project does not use an AI or Machine Learning model. Forecasting is performed using a statistical time-series approach.

---

## 📌 Project Overview

Climate variability and increasing temperatures make it important to understand historical temperature patterns and potential future conditions.

This project provides an interactive dashboard focused specifically on **Islamabad**, allowing users to explore historical climate observations and generate temperature forecasts based on available historical data.

The dashboard combines:

* Historical climate data analysis
* Temperature and humidity visualization
* Time-series forecasting
* Future temperature prediction
* Heatwave/temperature risk assessment
* Interactive charts and dashboard components

---

## 🚀 Key Features

* 📊 Historical climate data analysis for **Islamabad**
* 📅 Historical data covering **2005–2025**
* 🌡️ Temperature analysis and forecasting
* 💧 Humidity analysis
* 📈 Historical temperature trend visualization
* 🔮 Future temperature forecasting using a statistical time-series approach
* 🔄 Autoregressive future forecasting
* 🔥 Heatwave/temperature risk categorization
* 📍 Islamabad-focused climate analysis
* 🖥️ Interactive web dashboard
* 📉 Historical vs forecast temperature visualization

---

## ⚙️ How It Works

The forecasting workflow uses historical climate observations from Islamabad.

### Step 1 — Historical Data

Historical temperature and humidity observations are processed and prepared for analysis.

### Step 2 — Time-Series Input

A **30-day historical sequence** is used as the input window for forecasting future temperature conditions.

### Step 3 — Temperature Forecasting

A statistical time-series forecasting approach is used to generate future temperature values.

The forecasting process is **autoregressive**, meaning previously generated forecast values can be used as inputs for subsequent predictions.

### Step 4 — Risk Assessment

The predicted temperature conditions are evaluated to determine the corresponding temperature/heatwave risk category.

### Step 5 — Visualization

The dashboard presents:

* Historical temperature trends
* Forecast temperature trends
* Humidity information
* Predicted conditions
* Heatwave/temperature risk levels

---

## 🗂️ Project Scope

**Study Area:** Islamabad, Pakistan
**Historical Period:** 2005–2025
**Forecasting Approach:** Statistical Time-Series Forecasting
**Input Window:** 30 days
**Primary Variables:** Temperature and Humidity

---

## 🛠️ Technologies Used

* **Python**
* **Pandas**
* **NumPy**
* **Plotly**
* **Streamlit**
* **Time-Series Forecasting**
* **Data Preprocessing**
* **Data Visualization**

---

## 📊 Dashboard

The dashboard provides an interactive interface for exploring Islamabad's climate data and temperature forecasts.

Users can select a target date and analyze historical and forecast temperature trends through interactive visualizations.

---

## 🌍 Applications

The project can be useful for exploring:

* Heatwave preparedness
* Climate-risk assessment
* Temperature trend analysis
* Climate resilience
* Environmental monitoring
* Local climate research
* Data-driven decision making

---

## 📁 Project Structure

```text
Islamabad-Climate-Forecasting/
│
├── app.py
├── data/
│   └── climate_data.csv
│
├── requirements.txt
├── README.md
└── assets/
    └── dashboard_screenshot.png
```

> The exact file structure may vary depending on the final repository organization.

---

## ▶️ How to Run Locally

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Islamabad-Climate-Forecasting
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit application

```bash
streamlit run app.py
```

The dashboard will then be available in your browser.

---
## 🎯 Learning Outcomes

This project provided practical experience in:

* Climate data analysis
* Data preprocessing
* Statistical time-series forecasting
* Temperature trend analysis
* Data visualization
* Interactive dashboard development
* Python-based application development
* Climate and geospatial applications

---

## 👩‍💻 Developed By

**Ayesha**
Student, University of Kotli Azad Jammu and Kashmir

---

## 🤝 Acknowledgements

I would like to thank **AI Geo Navigators** for providing the opportunity to work on real-world climate and geospatial applications.

Special thanks to:

* **Asim Javid** — CEO, AI Geo Navigators
* **Owais Ali**
* **Rao Abdul Saboor**
* **Muhammad Ali** — Team Lead

for their guidance, support, and encouragement throughout the project.

---

## 📜 Disclaimer

This dashboard is developed for **educational, analytical, and research purposes**. Forecast results should not be considered official weather warnings or emergency predictions.

---

## 🔖 Topics

`Climate Data` `Climate Analysis` `Temperature Forecasting` `Time Series` `Heatwave Risk` `Python` `Streamlit` `Data Visualization` `Islamabad` `Pakistan` `GIS` `Climate Technology`
