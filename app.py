# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime, timedelta

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
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 0rem !important;
            max-width: 95% !important;
        }
        
        button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- LOADING API KEYS ---
FRED_API_KEY = st.secrets["FRED_API_KEY"]

if not FRED_API_KEY:
    st.error("FRED_API_KEY is missing! Ensure you have a /.streamlit/secrets.toml file in your project folder.")
    st.stop()

fred = Fred(api_key=FRED_API_KEY)

# --- SIDEBAR DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_market_data(start):
    tickers = {
        'S&P 500': '^GSPC', 
        'Dollar (DXY)': 'DX-Y.NYB', 
        'VIX': '^VIX', 
        '10Y Yield': '^TNX'
    }
    
    series_list = []
    
    for name, ticker_symbol in tickers.items():
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            hist = ticker_obj.history(start=start)
            if not hist.empty:
                close_prices = hist['Close']
                close_prices.name = name
                # Fix timezone BEFORE concat to prevent index errors
                close_prices.index = close_prices.index.tz_localize(None) 
                series_list.append(close_prices)
        except Exception as e:
            st.warning(f"Failed to fetch {name}: {e}")
            
    try:
        dff = fred.get_series('DFF', observation_start=start)
        dff.name = 'Fed Effective Rate'
        # Fix timezone BEFORE concat to prevent index errors
        dff.index = dff.index.tz_localize(None)
        series_list.append(dff)
    except Exception as e:
        st.warning(f"Failed to fetch Fed Rate: {e}")
            
    if series_list:
        df_market = pd.concat(series_list, axis=1, sort=True).ffill().dropna()
        return df_market
        
    return pd.DataFrame()

# --- SIDEBAR SETTINGS & METRICS ---
st.sidebar.title("Configuration")
days_back = st.sidebar.slider("History range (days)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

st.sidebar.markdown("---")
st.sidebar.markdown("**Daily change**")

with st.spinner("Fetching market data..."):
    df_market = get_market_data(start_date)

if not df_market.empty:
    for column in df_market.columns:
        # Remove consecutive duplicates to get the last unique price change for accurate delta calculation
        unique_prices = df_market[column].loc[(df_market[column].shift() != df_market[column])]
        
        if len(unique_prices) >= 2:
            current_price = unique_prices.iloc[-1]
            prev_price = unique_prices.iloc[-2]
            pct_change = ((current_price - prev_price) / prev_price) * 100
        else:
            current_price = df_market[column].iloc[-1]
            pct_change = 0.0
            
        if column in ['Fed Effective Rate', '10Y Yield']:
            st.sidebar.metric(label=column, value=f"{current_price:.2f}%", delta=None)
        else:
            st.sidebar.metric(label=column, value=f"{current_price:.2f}", delta=f"{pct_change:.2f}%")

# --- MAIN APPLICATION ---
if not df_market.empty:
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "System Liquidity", 
        "Market Indicators",
        "FED Dot Plot", 
        "Implied Volatility Surface",      
        "IV vs HV", 
        "Gamma Exposure"
    ])
    
    with tab1:
        plot_net_liquidity(start_date, fred)

    with tab2:
        plot_market_indicators(df_market, start_date, fred)

    with tab3:
        plot_fed_projections(fred)

    with tab4:
        render_iv_surface("SPY")
        
    with tab5:
        plot_iv_vs_hv(days_back)
        
    with tab6:
        plot_gamma_profile(fred)

else:
    st.warning("No data to display. Check your connection and API keys.")