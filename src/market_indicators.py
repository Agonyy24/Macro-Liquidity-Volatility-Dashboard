# src/market_indicators.py
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf

def plot_market_indicators(df_market, start_date, fred):
    # --- ROW 1 ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sentiment (VIX)")
        st.markdown("<span style='font-size:14px; color:gray;'>30-Day expected market volatility.</span>", unsafe_allow_html=True)
        fig_vix = go.Figure(data=[go.Scatter(x=df_market.index, y=df_market['VIX'], line=dict(color='red'))])
        fig_vix.update_layout(template='plotly_dark', height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_vix, width='stretch')
        
    with col2:
        st.subheader("Yield Curve (T10Y2Y)")
        st.markdown("<span style='font-size:14px; color:gray;'>Inversion signals recession. Un-inversion signals the crash.</span>", unsafe_allow_html=True)
        try:
            yield_curve = fred.get_series('T10Y2Y', observation_start=start_date)
            fig_yc = go.Figure(data=[go.Scatter(x=yield_curve.index, y=yield_curve.values, line=dict(color='purple'))])
            fig_yc.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Zero Line") 
            fig_yc.update_layout(template='plotly_dark', height=400, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_yc, width='stretch')
        except Exception as e:
            st.warning("Failed to fetch T10Y2Y from FRED.")

    st.markdown("---")

    # --- ROW 2 ---
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Credit Spreads (HY OAS)")
        st.markdown("<span style='font-size:14px; color:gray;'>ICE BofA US High Yield. Rising = Corporate default stress.</span>", unsafe_allow_html=True)
        try:
            # BAMLH0A0HYM2 is the official FRED ticker for High Yield Option-Adjusted Spread
            credit_spread = fred.get_series('BAMLH0A0HYM2', observation_start=start_date)
            fig_cs = go.Figure(data=[go.Scatter(x=credit_spread.index, y=credit_spread.values, line=dict(color='orange'))])
            fig_cs.update_layout(template='plotly_dark', height=400, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_cs, width='stretch')
        except Exception as e:
            st.warning("Failed to fetch Credit Spreads from FRED.")

    with col4:
        st.subheader("Tail Risk (SKEW Index)")
        st.markdown("<span style='font-size:14px; color:gray;'>Black Swan pricing. 100 = Normal, 140+ = Extreme Fear.</span>", unsafe_allow_html=True)
        try:
            skew = yf.Ticker('^SKEW').history(start=start_date)['Close']
            fig_skew = go.Figure(data=[go.Scatter(x=skew.index, y=skew.values, line=dict(color='cyan'))])
            
            # Add visual thresholds for normal vs high risk
            fig_skew.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Normal Risk", annotation_font_color="gray")
            fig_skew.add_hline(y=140, line_dash="dash", line_color="red", annotation_text="High Risk", annotation_font_color="red")
            
            fig_skew.update_layout(template='plotly_dark', height=400, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_skew, width='stretch')
        except Exception as e:
            st.warning("Failed to fetch SKEW from Yahoo Finance.")