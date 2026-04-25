# src/hv_vs_iv.py
import yfinance as yf
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def plot_iv_vs_hv(days_back):
    st.subheader("IV vs HV (Implied vs Historical Volatility)")
    st.markdown("<span style='font-size:14px; color:gray;'>Volatility Risk Premium (VRP). The shaded area represents the spread between market fear (VIX) and actual realized market moves.</span>", unsafe_allow_html=True)
    
    with st.spinner('Fetching price history and calculating volatility...'):
        
        today = pd.Timestamp.today().normalize()
        display_start = today - pd.Timedelta(days=days_back)
        
        # Add a 60-calendar-day hidden buffer to ensure the 21-day EWMA is fully "warmed up"
        fetch_start = display_start - pd.Timedelta(days=60)
        
        spy = yf.Ticker("SPY").history(start=fetch_start.strftime('%Y-%m-%d'))['Close']
        vix = yf.Ticker("^VIX").history(start=fetch_start.strftime('%Y-%m-%d'))['Close']
        
        spy.index = spy.index.tz_localize(None)
        vix.index = vix.index.tz_localize(None)
        
        df_vol = pd.DataFrame({'SPY': spy, 'VIX': vix}).dropna()
        
        # Log returns and Historical Volatility (HV)
        df_vol['Log_Ret'] = np.log(df_vol['SPY'] / df_vol['SPY'].shift(1))
        
        # Exponentially Weighted Moving Average (EWMA)
        df_vol['HV_21'] = df_vol['Log_Ret'].ewm(span=21, adjust=False).std() * np.sqrt(252) * 100
        
        df_vol = df_vol.dropna()
        
        # Cut off the warm-up buffer from EWMA
        df_vol = df_vol[df_vol.index >= display_start]

        fig = go.Figure()

        # Plot Implied Volatility (VIX)
        fig.add_trace(go.Scatter(
            x=df_vol.index, 
            y=df_vol['VIX'], 
            name='IV (Market Expectations - VIX)', 
            line=dict(color='orange', width=2),
            hovertemplate="<b>Date:</b> %{x}<br><b>IV:</b> %{y:.2f}%<extra></extra>"
        ))

        # Plot Historical Volatility (HV)
        fig.add_trace(go.Scatter(
            x=df_vol.index, 
            y=df_vol['HV_21'], 
            name='HV (Realized Volatility - SPY)', 
            line=dict(color='royalblue', width=2),
            fill='tonexty', # Visualizes the Volatility Risk Premium area
            fillcolor='rgba(255, 165, 0, 0.15)',
            hovertemplate="<b>Date:</b> %{x}<br><b>HV:</b> %{y:.2f}%<extra></extra>"
        ))

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Annualized Volatility (%)",
            template="plotly_dark",
            hovermode="x unified",
            height=500,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, width='stretch')