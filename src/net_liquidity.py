# src/net_liquidity.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def plot_net_liquidity(df_macro, df_market):
    st.header("Fed Net Liquidity vs S&P 500")
    st.markdown("Net Liquidity = Fed Balance Sheet (WALCL) - TGA - Reverse Repo.")
    
    # Combine data for plotting
    combined_df = pd.concat([df_macro['Net_Liquidity'], df_market['S&P 500']], axis=1).ffill().dropna()
    
    fig = go.Figure()
    
    # Y1 Axis: Liquidity
    fig.add_trace(go.Scatter(
        x=combined_df.index, y=combined_df['Net_Liquidity'], 
        name='Net Liquidity ($M)', line=dict(color='#00F5FF', width=2)
    ))
    
    # Y2 Axis: SP500
    fig.add_trace(go.Scatter(
        x=combined_df.index, y=combined_df['S&P 500'], 
        name='S&P 500', yaxis='y2', line=dict(color='#FFA500', width=1.5, dash='dot')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        height=600,
        hovermode='x unified',
        yaxis=dict(
            title=dict(text='Net Liquidity (Mln USD)', font=dict(color='#00F5FF')), 
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