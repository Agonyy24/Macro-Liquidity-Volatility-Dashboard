# src/iv_surface.py
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime
import streamlit as st
import time

@st.cache_data(ttl=3600)
def get_iv_surface_data(ticker_symbol="SPY"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Faster and safer spot price retrieval
        try:
            spot_price = ticker.fast_info['lastPrice']
        except Exception:
            # Fallback if fast_info fails
            hist = ticker.history(period="5d")
            if hist.empty:
                return None, None, None, None, "Failed to fetch underlying asset price."
            spot_price = hist['Close'].iloc[-1]
            
        expirations = ticker.options
        if not expirations:
            return None, None, None, None, "No options data available."

        # Fetch the first 10 expirations (includes nearest terms)
        selected_expirations = expirations[:10] 
        today = datetime.today().date()
        all_data = []

        for exp in selected_expirations:
            # Target anti-bot system
            time.sleep(0.5)
            try:
                opt = ticker.option_chain(exp)
                calls = opt.calls
                puts = opt.puts
                
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                if dte <= 0: dte = 0.5 # 0.5 days for 0-DTE options
                
                otm_puts = puts[puts['strike'] <= spot_price].copy()
                otm_calls = calls[calls['strike'] > spot_price].copy()
                
                clean_chain = pd.concat([otm_puts, otm_calls])
                
                # Filter by volume, open interest, and realistic IV bounds
                clean_chain = clean_chain[
                    (clean_chain['volume'] > 0) & 
                    (clean_chain['openInterest'] > 0) & 
                    (clean_chain['impliedVolatility'] > 0.01) &
                    (clean_chain['impliedVolatility'] < 3.0) 
                ]
                
                for _, row in clean_chain.iterrows():
                    all_data.append([row['strike'], dte, row['impliedVolatility']])
            except Exception:
                continue 
                
        if not all_data:
            return None, None, None, None, "Filters rejected all available options."

        df = pd.DataFrame(all_data, columns=['Strike', 'DTE', 'IV'])
        
        # Generate meshgrid for the 3D surface
        strike_grid = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
        dte_grid = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
        X, Y = np.meshgrid(strike_grid, dte_grid)
        
        # Two-step interpolation to eliminate "flat cliffs"
        Z_linear = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='linear')
        Z_nearest = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='nearest')
        
        # Fill NaN values (grid edges) with the nearest logical points
        Z = np.where(np.isnan(Z_linear), Z_nearest, Z_linear)

        return X, Y, Z, spot_price, None
    
    except Exception as e:
        return None, None, None, None, str(e)


def render_iv_surface(ticker_symbol="SPY"):
    """Main function to be called in the Streamlit dashboard."""
    st.subheader(f"Implied Volatility Surface ({ticker_symbol})")
    st.markdown("<span style='font-size:14px; color:gray;'>Constructed from liquid OTM options. Visualizes Term Structure and Volatility Skew.</span>", unsafe_allow_html=True)
    
    with st.spinner("Calculating 3D options grid (this may take a few seconds)..."):
        X, Y, Z, spot_price, error_msg = get_iv_surface_data(ticker_symbol)
        
        if error_msg:
            st.error(f"Failed to generate surface: {error_msg}")
        elif Z is not None:
            
            fig_iv = go.Figure()
            
            # --- MAIN IV SURFACE ---
            fig_iv.add_trace(go.Surface(
                z=Z, x=X, y=Y, 
                colorscale='Turbo', # Dynamic scale optimized for depth perception
                colorbar=dict(title='Implied Volatility', thickness=20, len=0.7),
                hovertemplate="<b>Strike:</b> %{x:.2f}<br><b>DTE:</b> %{y:.0f} days<br><b>IV:</b> %{z:.2%}<extra></extra>",
                contours=dict(
                    z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project_z=True) # Adds a 2D heat map on the floor
                )
            ))

            # --- ATM SPOT PRICE PLANE ---
            if spot_price:
                # Create grid for a vertical wall spanning Z and Y
                y_plane = np.array([Y.min(), Y.max()])
                z_plane = np.array([Z.min(), Z.max()])
                Y_plane, Z_plane = np.meshgrid(y_plane, z_plane)
                # Fix X to the current spot price
                X_plane = np.full_like(Y_plane, spot_price)

                fig_iv.add_trace(go.Surface(
                    x=X_plane, 
                    y=Y_plane, 
                    z=Z_plane,
                    colorscale=[[0, 'white'], [1, 'white']], # Clean white plane
                    opacity=0.15, # Highly transparent ghost wall
                    showscale=False, 
                    name='ATM Spot Price',
                    hoverinfo='skip' # Mouse ignores this layer
                ))

            # --- LAYOUT FORMATTING ---
            fig_iv.update_layout(
                scene=dict(
                    xaxis=dict(title='Strike Price', gridcolor='gray', showbackground=False),
                    yaxis=dict(title='Days to Expiry (DTE)', gridcolor='gray', showbackground=False),
                    zaxis=dict(title='Implied Volatility', gridcolor='gray', showbackground=False, tickformat=".0%"),
                    camera=dict(eye=dict(x=1.6, y=-1.6, z=0.6))
                ),
                height=700,
                margin=dict(l=0, r=0, b=0, t=30),
                template="plotly_dark"
            )
            
            st.plotly_chart(fig_iv, width='stretch')