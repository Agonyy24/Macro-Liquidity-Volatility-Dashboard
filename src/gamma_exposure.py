# src/gamma_exposure.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from scipy.stats import norm
import streamlit as st

# --- Helper Function: Calculate Gamma ---
def calc_gamma(S, K, T, r, sigma):
    # Protection against division by zero for very short-dated options
    T = np.maximum(T, 1e-5)
    sigma = np.maximum(sigma, 1e-5)
    
    # Black-Scholes formula for d1
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    # Gamma is the derivative of d1
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return gamma

# --- Main Dashboard Component ---
def plot_gamma_profile():
    st.subheader("Net Gamma Exposure (GEX) Profile")
    st.markdown("<span style='font-size:14px; color:gray;'>Market Maker hedging levels. Positive (Green) = Volatility suppression (Call Walls). Negative (Red) = Volatility acceleration (Put Walls).</span>", unsafe_allow_html=True)
    
    # DTE Slider
    max_dte = st.slider("Filter options by max Days to Expiry (DTE)", min_value=0, max_value=90, value=7)
    
    with st.spinner('Calculating Market Maker Gamma Exposure...'):
        try:
            ticker = yf.Ticker("SPY")
            spot_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Fetch multiple expirations to allow filtering
            expirations = ticker.options[:15] 
            
            gex_data = []
            
            for exp in expirations:
                # Normalize dates to remove hours/minutes for a clean daily comparison
                today_date = pd.Timestamp.today().normalize()
                exp_date = pd.to_datetime(exp).normalize()
                days_to_exp = (exp_date - today_date).days
                
                # --- SLIDER INTEGRATION ---
                # Skip options expiring beyond the selected DTE
                if days_to_exp > max_dte:
                    continue
                
                # Dirac Delta protection: Assume 0-DTE options have at least 0.5 days left
                T = max(days_to_exp, 0.5) / 365.0
                
                opt = ticker.option_chain(exp)
                
                # --- CALL Options ---
                calls = opt.calls
                # Calculate Gamma manually for each option in the chain
                calls['Gamma'] = calc_gamma(spot_price, calls['strike'], T, 0.04, calls['impliedVolatility'])
                # GEX = Open Interest * Gamma * Contract Size (100) * Spot Price
                calls['GEX'] = calls['openInterest'] * calls['Gamma'] * 100 * spot_price
                
                # --- PUT Options ---
                puts = opt.puts
                puts['Gamma'] = calc_gamma(spot_price, puts['strike'], T, 0.04, puts['impliedVolatility'])
                # Assume customers buy Puts for insurance, making Market Maker exposure negative
                puts['GEX'] = -puts['openInterest'] * puts['Gamma'] * 100 * spot_price
                
                # Store calculations
                gex_data.append(calls[['strike', 'GEX']])
                gex_data.append(puts[['strike', 'GEX']])
                
            # Combine and sum GEX by Strike Price
            df_gex = pd.concat(gex_data)
            gex_profile = df_gex.groupby('strike')['GEX'].sum().reset_index()
            
            # Filter for strikes within +/- 10% of spot price to remove extreme OTM noise
            gex_profile = gex_profile[(gex_profile['strike'] > spot_price * 0.9) & (gex_profile['strike'] < spot_price * 1.1)]

            # --- Draw the Chart ---
            fig = go.Figure()
            
            # Color bars: Green (Positive GEX = Shock absorber), Red (Negative GEX = Accelerator)
            colors = ['#ff4b4b' if val < 0 else '#00ff00' for val in gex_profile['GEX']]
            
            fig.add_trace(go.Bar(
                x=gex_profile['strike'],
                y=gex_profile['GEX'],
                marker_color=colors,
                name='Net GEX',
                hovertemplate="<b>Strike:</b> %{x}<br><b>Net GEX:</b> %{y:,.0f}<extra></extra>"
            ))
            
            # Highlight current spot price
            fig.add_vline(
                x=spot_price, 
                line_dash="dash", 
                line_color="gold", 
                annotation_text=f" Spot Price: {spot_price:.2f} ",
                annotation_position="top left",
                annotation_font=dict(color="gold")
            )

            fig.update_layout(
                xaxis_title="Strike Price",
                yaxis_title="Gamma Exposure (Wall Size)",
                template="plotly_dark",
                bargap=0.2,
                height=500,
                margin=dict(l=0, r=0, t=30, b=0),
                showlegend=False
            )
            
            st.plotly_chart(fig, width='stretch')
            
        except Exception as e:
            st.error(f"Error calculating GEX: {e}")