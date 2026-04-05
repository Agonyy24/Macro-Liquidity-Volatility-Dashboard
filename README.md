# Macro Liquidity & Volatility Dashboard

An educational dashboard built with Streamlit to visualize macroeconomic liquidity and options market tail-risk. This project serves as a practical tool for understanding how central bank mechanics and options data interact with the broader market.

![Dashboard Preview](screenshots/ss1.png)

## Features

* **Macro Liquidity Engine:** Tracks Federal Reserve Net Liquidity (WALCL - TGA - RRP) against the S&P 500, adjusting dynamically to show true systemic bank reserves in Trillions ($T).
* **Options Market Analysis:** Includes interactive 3D Implied Volatility Surfaces, IV vs HV comparisons, and Gamma Exposure profiles.
* **Fed Policy Tracking:** Visualizes the FED Dot Plot and implied rate paths.
* **Live Sidebar Dashboard:** Tracking of daily changes in the S&P 500, DXY, VIX, 10Y Yield, and the Fed Effective Rate.

## Tech Stack

* **Frontend:** Streamlit
* **Data Processing:** Pandas, NumPy, SciPy
* **Visualization:** Plotly
* **Market Data:** yfinance / FRED Data

## Local Setup

1. **Clone the repository**
2. **Install dependecies:**
```pip install -r requirements.txt```
3. **Configure API Keys (Streamlit Secrets):**
```FRED_API_KEY = "sk-your-secret-key-here"```
You can get free FRED API key here -> [FRED API](https://fred.stlouisfed.org/docs/api/fred)
4. **Run the App:**
```streamlit run app.py```