import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from scipy.interpolate import griddata
import os
from dotenv import load_dotenv
from iv_surface import render_iv_surface

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Macro Quant Dashboard", layout="wide")

# --- ŁADOWANIE KLUCZY API ---
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

if not FRED_API_KEY:
    st.error("Brak klucza FRED_API_KEY! Upewnij się, że masz plik .env w folderze z projektem.")
    st.stop()

fred = Fred(api_key=FRED_API_KEY)

# --- USTAWIENIA BOCZNE (SIDEBAR) ---
st.sidebar.title("Parametry")
days_back = st.sidebar.slider("Zakres historii (dni)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

# --- POBIERANIE DANYCH ---
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
        st.error(f"Błąd API FRED: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_market_data(start):
    tickers = {
        'S&P 500': '^GSPC', 
        'Dolar (DXY)': 'DX-Y.NYB', 
        'VIX': '^VIX', 
        '10Y Yield': '^TNX'
    }
    
    series_list = []
    
    # Pobieramy każdy ticker osobno - omijamy błędy MultiIndex!
    for name, ticker_symbol in tickers.items():
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            hist = ticker_obj.history(start=start)
            if not hist.empty:
                close_prices = hist['Close']
                close_prices.name = name
                series_list.append(close_prices)
        except Exception as e:
            st.warning(f"Nie udało się pobrać {name}: {e}")
            
    if series_list:
        # Łączymy wszystkie serie po dacie i wypełniamy braki (np. weekendy)
        df_market = pd.concat(series_list, axis=1).ffill().dropna()
        # Upewniamy się, że indeks nie ma strefy czasowej (tz-naive), aby pasował do FRED
        df_market.index = df_market.index.tz_localize(None)
        return df_market
    return pd.DataFrame()

# --- GŁÓWNA APLIKACJA ---
st.title("Macro & Liquidity Dashboard")

# Pobranie danych
with st.spinner("Pobieranie danych rynkowych i makro..."):
    df_macro = get_macro_data(start_date)
    df_market = get_market_data(start_date)

if not df_macro.empty and not df_market.empty:
    
    # KARTY Z WYNIKAMI (METRICS)
    st.subheader("Bieżące notowania")
    last_prices = df_market.iloc[-1]
    prev_prices = df_market.iloc[-2]
    
    cols = st.columns(4)
    for i, (name, price) in enumerate(last_prices.items()):
        change = ((price - prev_prices[name]) / prev_prices[name]) * 100
        cols[i].metric(name, f"{price:.2f}", f"{change:.2f}%")
        
    st.markdown("---")
    
    # ZAKŁADKI (TABS)
    tab1, tab2, tab3 = st.tabs(["Płynność Systemowa", "Wskaźniki Rynkowe", "Implied Voltality Surface"])
    
    with tab1:
        st.header("Fed Net Liquidity vs S&P 500")
        st.markdown("Płynność netto = Bilans Fed (WALCL) - TGA - Reverse Repo. **Złota zasada:** Podążaj za niebieską linią.")
        
        # Łączymy dane do wykresu
        combined_df = pd.concat([df_macro['Net_Liquidity'], df_market['S&P 500']], axis=1).ffill().dropna()
        
        fig = go.Figure()
        # Oś Y1: Płynność
        fig.add_trace(go.Scatter(
            x=combined_df.index, y=combined_df['Net_Liquidity'], 
            name='Net Liquidity ($M)', line=dict(color='#00F5FF', width=2)
        ))
        # Oś Y2: SP500
        fig.add_trace(go.Scatter(
            x=combined_df.index, y=combined_df['S&P 500'], 
            name='S&P 500', yaxis='y2', line=dict(color='#FFA500', width=1.5, dash='dot')
        ))
        
        fig.update_layout(
                    template='plotly_dark',
                    height=600,
                    hovermode='x unified',
                    yaxis=dict(
                        title=dict(text='Płynność Netto (Mln USD)', font=dict(color='#00F5FF')), 
                        tickfont=dict(color='#00F5FF')
                    ),
                    yaxis2=dict(
                        title=dict(text='S&P 500', font=dict(color='#FFA500')), 
                        tickfont=dict(color='#FFA500'), 
                        overlaying='y', 
                        side='right'
                    ),
                    legend=dict(x=0.01, y=0.99)
                )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sentyment (VIX)")
            fig_vix = go.Figure(data=[go.Scatter(x=df_market.index, y=df_market['VIX'], line=dict(color='red'))])
            fig_vix.update_layout(template='plotly_dark', height=400)
            st.plotly_chart(fig_vix, use_container_width=True)
            
        with col2:
            st.subheader("Krzywa Rentowności (T10Y2Y)")
            try:
                yield_curve = fred.get_series('T10Y2Y', observation_start=start_date)
                fig_yc = go.Figure(data=[go.Scatter(x=yield_curve.index, y=yield_curve.values, line=dict(color='purple'))])
                fig_yc.add_hline(y=0, line_dash="dash", line_color="white") # Linia zera
                fig_yc.update_layout(template='plotly_dark', height=400)
                st.plotly_chart(fig_yc, use_container_width=True)
            except Exception as e:
                st.warning("Nie udało się pobrać T10Y2Y z FRED.")

    with tab3:
        render_iv_surface("SPY")

else:
    st.warning("Brak danych do wyświetlenia. Sprawdź połączenie i klucze API.")