import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime
import streamlit as st
import time

# EXTRACTION STAGE (I/O & Caching)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_raw_options_data(ticker_symbol="SPY"):
    """Fetches raw OTM options chains and the underlying asset price from yfinance."""
    ticker = yf.Ticker(ticker_symbol)
    
    # Fetch Spot Price
    try:
        spot_price = ticker.fast_info['lastPrice']
    except Exception:
        hist = ticker.history(period="5d")
        if hist.empty:
            raise ValueError("Failed to fetch underlying asset price.")
        spot_price = hist['Close'].iloc[-1]
        
    expirations = ticker.options
    if not expirations:
        raise ValueError("No options data available.")

    today = datetime.today().date()
    raw_data_frames = []

    # Fetch the nearest 10 expiration dates
    for exp in expirations[:10]:
        time.sleep(0.5)  # Anti-bot delay
        try:
            opt = ticker.option_chain(exp)
            calls, puts = opt.calls, opt.puts
            
            exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
            dte = max((exp_date - today).days, 0.5) # Minimum 0.5 DTE
            
            # Pre-filtering: Keep only OTM options
            otm_puts = puts[puts['strike'] <= spot_price].copy()
            otm_calls = calls[calls['strike'] > spot_price].copy()
            
            chain = pd.concat([otm_puts, otm_calls])
            chain['DTE'] = dte
            raw_data_frames.append(chain)
            
        except Exception:
            continue 
            
    if not raw_data_frames:
        raise ValueError("Failed to download any valid option chains.")

    raw_df = pd.concat(raw_data_frames, ignore_index=True)
    return raw_df, spot_price


# TRANSFORMATION STAGE (Cleaning)

def filter_liquid_options(df: pd.DataFrame) -> pd.DataFrame:
    """Filters raw data for liquidity and reasonable IV bounds."""
    clean_df = df[
        (df['volume'] > 0) & 
        (df['openInterest'] > 0) & 
        (df['impliedVolatility'].between(0.01, 3.0))
    ].copy()
    
    if clean_df.empty:
        raise ValueError("Filters rejected all available options.")
        
    # Standardize column names for further calculations
    return clean_df[['strike', 'DTE', 'impliedVolatility']].rename(
        columns={'strike': 'Strike', 'impliedVolatility': 'IV'}
    )


# MODELING STAGE (Math)

def generate_surface_mesh(df: pd.DataFrame):
    """Generates a 3D grid using dual spatial interpolation."""
    strike_grid = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
    dte_grid = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
    X, Y = np.meshgrid(strike_grid, dte_grid)
    
    # Interpolation (linear with nearest-neighbor fallback at the edges)
    Z_linear = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='linear')
    Z_nearest = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='nearest')
    
    Z = np.where(np.isnan(Z_linear), Z_nearest, Z_linear)
    return X, Y, Z


# MAIN DATA PIPELINE

def process_iv_surface(ticker_symbol: str):
    """Connects the entire process into one readable pipeline."""
    try:
        # (Utilizing cache)
        raw_df, spot_price = fetch_raw_options_data(ticker_symbol)
        
        # Transformation and Modeling (On-the-fly, fast calculations)
        X, Y, Z = (
            raw_df
            .pipe(filter_liquid_options)
            .pipe(generate_surface_mesh)
        )
        
        return X, Y, Z, spot_price, None
        
    except Exception as e:
        # Clean error handling passed to the interface
        return None, None, None, None, str(e)


# USER INTERFACE (Streamlit & Plotly)

def render_iv_surface(ticker_symbol="SPY"):
    """Renders the component in the Streamlit dashboard."""
    st.subheader(f"Implied Volatility Surface ({ticker_symbol})")
    st.markdown("<span style='font-size:14px; color:gray;'>Constructed from liquid OTM options. Visualizes Term Structure and Volatility Skew.</span>", unsafe_allow_html=True)
    
    with st.spinner("Fetching data and calculating 3D surface..."):
        # Call the main pipeline
        X, Y, Z, spot_price, error_msg = process_iv_surface(ticker_symbol)
        
        if error_msg:
            st.error(f"Failed to generate surface: {error_msg}")
        elif Z is not None:
            
            fig_iv = go.Figure()
            
            # --- MAIN IV SURFACE ---
            fig_iv.add_trace(go.Surface(
                z=Z, x=X, y=Y, 
                colorscale='Turbo',
                colorbar=dict(title='Implied Volatility', thickness=20, len=0.7),
                hovertemplate="<b>Strike:</b> %{x:.2f}<br><b>DTE:</b> %{y:.0f} days<br><b>IV:</b> %{z:.2%}<extra></extra>",
                contours=dict(
                    z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project_z=True)
                )
            ))

            # --- ATM SPOT PRICE PLANE ---
            if spot_price:
                y_plane = np.array([Y.min(), Y.max()])
                z_plane = np.array([Z.min(), Z.max()])
                Y_plane, Z_plane = np.meshgrid(y_plane, z_plane)
                X_plane = np.full_like(Y_plane, spot_price)

                fig_iv.add_trace(go.Surface(
                    x=X_plane, 
                    y=Y_plane, 
                    z=Z_plane,
                    colorscale=[[0, 'white'], [1, 'white']], 
                    opacity=0.15, 
                    showscale=False, 
                    name='ATM Spot Price',
                    hoverinfo='skip'
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