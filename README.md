# Macro Liquidity & Volatility Dashboard

An educational dashboard built with Streamlit to visualize macroeconomic liquidity and options market tail-risk.

![Dashboard Preview](screenshots/ss1.png)

## Features

* **Macro Liquidity Engine:** Tracks Federal Reserve Net Liquidity (WALCL - TGA - RRP) against the S&P 500.
* **Options Market Analysis:** Includes interactive 3D Implied Volatility Surfaces, IV vs HV comparisons, and Gamma Exposure profiles.
* **Fed Policy Tracking:** Visualizes the FED Dot Plot and implied rate paths.
* **Live Sidebar Dashboard:** Tracking of daily changes in the S&P 500, DXY, VIX, 10Y Yield, and the Fed Effective Rate.

## Tech Stack

* **Frontend:** Streamlit
* **Data Processing:** Pandas, NumPy, SciPy
* **Visualization:** Plotly
* **Market Data:** yfinance / FRED Data

## Local Setup (Recommended) 
Running the application locally is **highly recommended** due to Yahoo Finance API rate-limiting on shared cloud environments (e.g., Streamlit Cloud). Local execution uses your dedicated IP, ensuring much higher stability for options data fetching.
1. **Clone the repository**
2. **Install dependecies:**
```pip install -r requirements.txt```
3. **Configure API Keys (Streamlit Secrets):**
```Macro-Liquidity-Volatility-Dashboard/.streamlit/secrets.toml``` \
```FRED_API_KEY = "sk-your-secret-key-here"``` \
You can get obtain your free FRED API key here -> [FRED API](https://fred.stlouisfed.org/docs/api/fred)
4. **Run the App:**
```streamlit run app.py```

##  Important Note on Data Availability (After-Hours Behavior)

Please bear in mind that this dashboard relies on the free Yahoo Finance API (`yfinance`) for live options chain data. While I have done my best to catch these errors, you may encounter warnings about **empty charts, zeroed-out Net GEX, or missing IV Surfaces** if you run the application during overnight or pre-market hours.

**Why does this happen?**
Unlike paid institutional data feeds that provide stable End-of-Day snapshots, Yahoo Finance mirrors the active state of broker routing systems. While data usually lasts for several hours after the market closes (and through the weekend), a "system reset" occurs in the middle of the night / early morning before the next trading session (this is from my own experience - unfortunately, I couldn't find any precise information regarding the exact hours of this reset).

**The Solution:**
For accurate analysis and visualization, **please run this dashboard during active US market hours (9:30 AM - 4:00 PM EST) or shortly after**. If you wish to develop or backtest after hours, it is recommended to cache an intraday `.csv` snapshot of the options chain and route the dashboard to read from your local file.
