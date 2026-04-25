# src/fed_dots.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

@st.cache_data(ttl=86400, show_spinner=False)
def get_fed_projections_data(_fred):
    df_fed = pd.DataFrame({
        'Median Consensus': _fred.get_series('FEDTARMD'),
        'High (Hawkish)': _fred.get_series('FEDTARRH'),
        'Low (Dovish)': _fred.get_series('FEDTARRL')
    }).dropna()

    current_year = pd.Timestamp.now().year
    df_fed = df_fed[df_fed.index.year >= current_year]
    
    return df_fed

def plot_fed_projections(fred):
    st.subheader("FED Dot Plot (Range & Median)")
    st.markdown("<span style='font-size:14px; color:gray;'>Summary of Economic Projections (SEP). Shows the range of Federal Reserve officials' target interest rates.</span>", unsafe_allow_html=True)
    
    try:
        with st.spinner("Fetching FED projections..."):
            df_fed = get_fed_projections_data(fred)

        if df_fed.empty:
            st.warning("No projection data available at the moment.")
            return

        fig = go.Figure()

        # Range lines
        for idx, row in df_fed.iterrows():
            fig.add_trace(go.Scatter(
                x=[idx.year, idx.year], 
                y=[row['Low (Dovish)'], row['High (Hawkish)']],
                mode='lines',
                line=dict(color='rgba(255, 255, 255, 0.2)', width=3, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))

        # Dots and median line
        fig.add_trace(go.Scatter(
            x=df_fed.index.year, 
            y=df_fed['High (Hawkish)'], 
            mode='markers', 
            name='Highest Projection', 
            marker=dict(color='#ff4b4b', size=10, symbol='triangle-up'),
            hovertemplate="<b>Year:</b> %{x}<br><b>Rate:</b> %{y:.2f}%<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_fed.index.year, 
            y=df_fed['Low (Dovish)'], 
            mode='markers', 
            name='Lowest Projection', 
            marker=dict(color='#00ff00', size=10, symbol='triangle-down'),
            hovertemplate="<b>Year:</b> %{x}<br><b>Rate:</b> %{y:.2f}%<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_fed.index.year, 
            y=df_fed['Median Consensus'], 
            mode='lines+markers', 
            name='Median (Consensus)', 
            line=dict(color='gold', width=3), 
            marker=dict(size=12, symbol='circle'),
            hovertemplate="<b>Year:</b> %{x}<br><b>Median Rate:</b> %{y:.2f}%<extra></extra>"
        ))

        # Layout formatting
        fig.update_layout(
            xaxis_title="Projection Year",
            yaxis_title="Target Interest Rate",
            xaxis=dict(tickmode='linear', dtick=1, gridcolor='rgba(128, 128, 128, 0.2)'),
            yaxis=dict(ticksuffix="%", gridcolor='rgba(128, 128, 128, 0.2)'),
            template="plotly_dark",
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
        
    except Exception as e:
        st.error(f"Error generating FED Dot Plot: {e}")