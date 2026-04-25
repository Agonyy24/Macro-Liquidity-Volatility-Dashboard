# src/net_liquidity.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

@st.cache_data(ttl=300)
def get_liquidity_data(start_date, _fred):
    try:
        # Fetch Macro Data from FRED
        fed_balance = _fred.get_series('WALCL', observation_start=start_date)
        tga = _fred.get_series('WTREGEN', observation_start=start_date)
        rrp = _fred.get_series('RRPONTSYD', observation_start=start_date)
        
        df_macro = pd.DataFrame({'WALCL': fed_balance, 'TGA': tga, 'RRP': rrp}).ffill()
        df_macro['Net_Liquidity'] = (df_macro['WALCL'] - df_macro['TGA'] - df_macro['RRP']) * 1000000 
        
        # Fetch SP500 from Yahoo
        sp500 = yf.Ticker('^GSPC').history(start=start_date)['Close']
        sp500.name = 'S&P 500'
        sp500.index = sp500.index.tz_localize(None)
        
        # Combine both
        combined_df = pd.concat([df_macro['Net_Liquidity'], sp500], axis=1).ffill().dropna()
        return combined_df
        
    except Exception as e:
        st.error(f"Error fetching liquidity data: {e}")
        return pd.DataFrame()

def plot_net_liquidity(start_date, fred):
    st.subheader("Fed Net Liquidity vs S&P 500")
    st.markdown("<span style='font-size:14px; color:gray;'>Net Liquidity = Fed Balance Sheet (WALCL) - TGA - Reverse Repo.</span>", unsafe_allow_html=True)
    
    combined_df = get_liquidity_data(start_date, fred)
    
    if combined_df.empty:
        st.warning("No data available for Net Liquidity.")
        return

    fig = go.Figure()
    
    # X Axis Liquidity
    fig.add_trace(go.Scatter(
        x=combined_df.index, y=combined_df['Net_Liquidity'], 
        name='Net Liquidity ($T)', line=dict(color='#00F5FF', width=2)
    ))
    
    # Y Axis SP500
    fig.add_trace(go.Scatter(
        x=combined_df.index, y=combined_df['S&P 500'], 
        name='S&P 500', yaxis='y2', line=dict(color='#FFA500', width=1.5, dash='dot')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        height=600,
        hovermode='x unified',
        yaxis=dict(
            title=dict(text='Net Liquidity', font=dict(color='#00F5FF')), 
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
    
    st.plotly_chart(fig, width='stretch')