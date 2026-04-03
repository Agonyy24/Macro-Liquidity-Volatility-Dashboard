# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# --- IMPORT MODULARIZED COMPONENTS ---
from src.iv_surface import render_iv_surface
from src.fed_dots import plot_fed_projections
from src.hv_vs_iv import plot_iv_vs_hv
from src.gamma_exposure import plot_gamma_profile
from src.net_liquidity import plot_net_liquidity
from src.market_indicators import plot_market_indicators

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Macro Quant Dashboard", layout="wide")

st.markdown("""
    <style>
        /* 1. Fix padding so tabs don't hide under the top menu bar */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 0rem !important;
            max-width: 95% !important;
        }
        
        /* 2. Make the tabs larger and bolder */
        button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- LOAD API KEYS ---
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

if not FRED_API_KEY:
    st.error("FRED_API_KEY is missing! Ensure you have a .env file in your project folder.")
    st.stop()

fred = Fred(api_key=FRED_API_KEY)

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def get_macro_data(start):
    try:
        fed_balance = fred.get_series('WALCL', observation_start=start)
        tga = fred.get_series('WTREGEN', observation_start=start)
        rrp = fred.get_series('RRPONTSYD', observation_start=start)
        
        df = pd.DataFrame({'WALCL': fed_balance, 'TGA': tga, 'RRP': rrp}).ffill()
        df['Net_Liquidity'] = df['WALCL'] - df['TGA'] - df['RRP']
        return df
    except Exception as e:
        st.error(f"FRED API Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_market_data(start):
    tickers = {
        'S&P 500': '^GSPC', 
        'Dollar (DXY)': 'DX-Y.NYB', 
        'VIX': '^VIX', 
        '10Y Yield': '^TNX'
    }
    
    series_list = []
    
    # 1. Fetch market data from Yahoo Finance
    for name, ticker_symbol in tickers.items():
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            hist = ticker_obj.history(start=start)
            if not hist.empty:
                close_prices = hist['Close']
                close_prices.name = name
                # Fix timezone BEFORE concat to prevent Pandas index errors
                close_prices.index = close_prices.index.tz_localize(None)
                series_list.append(close_prices)
        except Exception as e:
            st.warning(f"Failed to fetch {name}: {e}")
            
    # 2. Fetch Effective Federal Funds Rate from FRED
    try:
        # DFF is the official ticker for the daily Effective Fed Funds Rate
        dff = fred.get_series('DFF', observation_start=start)
        dff.name = 'Fed Rate'
        dff.index = dff.index.tz_localize(None)
        series_list.append(dff)
    except Exception as e:
        st.warning(f"Failed to fetch Fed Rate: {e}")
            
    # 3. Combine everything
    if series_list:
        df_market = pd.concat(series_list, axis=1).ffill().dropna()
        return df_market
        
    return pd.DataFrame()

# --- SIDEBAR SETTINGS & METRICS ---
st.sidebar.title("Configuration")
days_back = st.sidebar.slider("History range (days)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

st.sidebar.markdown("---")

with st.spinner("Fetching data..."):
    df_macro = get_macro_data(start_date)
    df_market = get_market_data(start_date)

if not df_market.empty:
    # Safely calculate % change bypassing the weekend ffill() issue
    for column in df_market.columns:
        # Drop consecutive duplicates to find the actual last two trading days
        unique_prices = df_market[column].loc[(df_market[column].shift() != df_market[column])]
        
        if len(unique_prices) >= 2:
            current_price = unique_prices.iloc[-1]
            prev_price = unique_prices.iloc[-2]
            pct_change = ((current_price - prev_price) / prev_price) * 100
        else:
            current_price = df_market[column].iloc[-1]
            pct_change = 0.0
            
        st.sidebar.metric(label=column, value=f"{current_price:.2f}", delta=f"{pct_change:.2f}%")

# --- MAIN APPLICATION (FULL SCREEN TABS) ---
if not df_macro.empty and not df_market.empty:
    
    # TABS ROUTING
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "System Liquidity", 
        "Market Indicators", 
        "Implied Volatility Surface", 
        "FED Dot Plot", 
        "IV vs HV", 
        "Gamma Exposure"
    ])
    
    with tab1:
        plot_net_liquidity(df_macro, df_market)

    with tab2:
        plot_market_indicators(df_market, start_date, fred)

    with tab3:
        render_iv_surface("SPY")

    with tab4:
        plot_fed_projections()
        
    with tab5:
        plot_iv_vs_hv(days_back)
        
    with tab6:
        plot_gamma_profile()

else:
    st.warning("No data to display. Check your connection and API keys.")