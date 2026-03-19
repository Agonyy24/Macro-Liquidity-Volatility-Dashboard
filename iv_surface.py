# iv_surface.py
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime
import streamlit as st

@st.cache_data(ttl=3600)
def get_iv_surface_data(ticker_symbol="SPY"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        spot_price = ticker.history(period="1d")['Close'].iloc[-1]
        expirations = ticker.options
        
        if not expirations:
            return None, None, None, "Brak danych o opcjach."

        selected_expirations = expirations[1:9]
        today = datetime.today()
        all_data = []

        for exp in selected_expirations:
            try:
                opt = ticker.option_chain(exp)
                calls = opt.calls
                puts = opt.puts
                
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - today).days
                if dte <= 0: dte = 1 
                
                otm_puts = puts[puts['strike'] <= spot_price].copy()
                otm_calls = calls[calls['strike'] > spot_price].copy()
                
                clean_chain = pd.concat([otm_puts, otm_calls])
                
                clean_chain = clean_chain[
                    (clean_chain['volume'] > 0) & 
                    (clean_chain['impliedVolatility'] > 0.01) &
                    (clean_chain['impliedVolatility'] < 1.5) 
                ]
                
                for _, row in clean_chain.iterrows():
                    all_data.append([row['strike'], dte, row['impliedVolatility']])
            except Exception:
                continue 
                
        if not all_data:
            return None, None, None, "Filtry odrzuciły wszystkie opcje."

        df = pd.DataFrame(all_data, columns=['Strike', 'DTE', 'IV'])
        
        strike_grid = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
        dte_grid = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
        X, Y = np.meshgrid(strike_grid, dte_grid)
        
        Z = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='cubic')
        
        mean_z = np.nanmean(Z)
        Z = np.nan_to_num(Z, nan=mean_z if not np.isnan(mean_z) else 0)

        return X, Y, Z, None
    except Exception as e:
        return None, None, None, str(e)

def render_iv_surface(ticker_symbol="SPY"):
    """Funkcja główna do wywołania w dashboardzie."""
    st.header(f"Implied Volatility Surface ({ticker_symbol})")
    st.markdown("Wykres zmontowany z płynnych opcji OTM (Out-of-the-Money). Pozwala ocenić *Term Structure* oraz *Volatility Skew*.")
    
    with st.spinner("Przeliczanie siatki 3D dla opcji (to zajmie kilka sekund)..."):
        X, Y, Z, error_msg = get_iv_surface_data(ticker_symbol)
        
        if error_msg:
            st.error(f"Nie udało się wygenerować powierzchni: {error_msg}")
        elif Z is not None:
            fig_iv = go.Figure(data=[go.Surface(
                z=Z, x=X, y=Y, 
                colorscale='Plasma',
                colorbar_title='IV (Zmienność)'
            )])

            fig_iv.update_layout(
                scene=dict(
                    xaxis_title='Cena Wykonania (Strike)',
                    yaxis_title='Dni do Wygaśnięcia (DTE)',
                    zaxis_title='Implied Volatility (IV)',
                    camera=dict(eye=dict(x=1.5, y=-1.5, z=0.5))
                ),
                height=800,
                margin=dict(l=0, r=0, b=0, t=30),
                template="plotly_dark"
            )
            
            st.plotly_chart(fig_iv, use_container_width=True)