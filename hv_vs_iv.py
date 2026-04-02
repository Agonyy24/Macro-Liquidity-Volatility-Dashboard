import yfinance as yf
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def plot_iv_vs_hv():
    st.subheader("IV vs HV (Zmienność Implikowana a Historyczna)")
    
    with st.spinner('Pobieranie historii cen i wyliczanie zmienności...'):
        # 1. Pobieramy WIĘCEJ danych (2 lata) dla "rozgrzania" wskaźników
        spy = yf.Ticker("SPY").history(period="2y")['Close']
        vix = yf.Ticker("^VIX").history(period="2y")['Close']
        
        spy.index = spy.index.tz_localize(None)
        vix.index = vix.index.tz_localize(None)
        
        df_vol = pd.DataFrame({'SPY': spy, 'VIX': vix}).dropna()
        
        # 2. Obliczamy zwroty i HV dla całych 2 lat
        df_vol['Log_Ret'] = np.log(df_vol['SPY'] / df_vol['SPY'].shift(1))
        # Stara wersja (Prymitywne okno, robi schodki):
        # df_vol['HV_21'] = df_vol['Log_Ret'].rolling(window=21).std() * np.sqrt(252) * 100

        # Nowa wersja Quanta (EWMA - Wygasza stare wstrząsy płynnie, brak schodków!):
        df_vol['HV_21'] = df_vol['Log_Ret'].ewm(span=21, adjust=False).std() * np.sqrt(252) * 100
        
        df_vol = df_vol.dropna()
        
        # 3. ZŁOTY FIX: Odcinamy "rozgrzewkę". Zostawiamy tylko ostatnie 252 sesje giełdowe (ok. 1 rok)
        df_vol = df_vol.tail(252)

        fig = go.Figure()

        # Rysujemy Implied Volatility (VIX)
        fig.add_trace(go.Scatter(
            x=df_vol.index, y=df_vol['VIX'], 
            name='IV (Oczekiwania Rynku - VIX)', 
            line=dict(color='orange', width=2)
        ))

        # Rysujemy Historical Volatility (HV)
        fig.add_trace(go.Scatter(
            x=df_vol.index, y=df_vol['HV_21'], 
            name='HV (Faktyczne Wahania SPY)', 
            line=dict(color='royalblue', width=2),
            fill='tonexty', # Wizualizuje obszar Premii za Ryzyko (VRP)
            fillcolor='rgba(255, 165, 0, 0.1)'
        ))

        fig.update_layout(
            title="Volatility Risk Premium (Oczekiwania vs Rzeczywistość)",
            xaxis_title="Data",
            yaxis_title="Zmienność Zannualizowana (%)",
            template="plotly_dark",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)