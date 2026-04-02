import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fredapi import Fred
import os
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()
FRED_API_KEY = os.getenv('FRED_API_KEY')

def plot_fed_projections():
    st.subheader("Oczekiwania FED (Zasięg i Mediana)")
    
    if not FRED_API_KEY:
        st.warning("Brak klucza FRED_API_KEY w pliku .env!")
        return

    try:
        fred = Fred(api_key=FRED_API_KEY)
        
        # Pobieranie danych: Mediana, High, Low
        # FRED zwraca roczne projekcje (index to zazwyczaj 1 stycznia danego roku docelowego)
       # ZŁOTY FIX: Poprawione, oficjalne kody (Series IDs) z bazy FRED
        df_fed = pd.DataFrame({
            'Mediana': fred.get_series('FEDTARMD'),
            'Najwyższa (Jastrząbie)': fred.get_series('FEDTARRH'),
            'Najniższa (Gołębie)': fred.get_series('FEDTARRL')
        }).dropna()

        # Interesują nas tylko obecne i przyszłe lata
        current_year = pd.Timestamp.now().year
        df_fed = df_fed[df_fed.index.year >= current_year]

        fig = go.Figure()

        # Linie zasięgu (od Low do High)
        for idx, row in df_fed.iterrows():
            fig.add_trace(go.Scatter(
                x=[idx.year, idx.year], 
                y=[row['Najniższa (Gołębie)'], row['Najwyższa (Jastrząbie)']],
                mode='lines',
                line=dict(color='gray', width=2),
                showlegend=False
            ))

        # Dodajemy kropki i medianę
        fig.add_trace(go.Scatter(x=df_fed.index.year, y=df_fed['Najwyższa (Jastrząbie)'], mode='markers', name='Max FED', marker=dict(color='red', size=10)))
        fig.add_trace(go.Scatter(x=df_fed.index.year, y=df_fed['Najniższa (Gołębie)'], mode='markers', name='Min FED', marker=dict(color='green', size=10)))
        fig.add_trace(go.Scatter(x=df_fed.index.year, y=df_fed['Mediana'], mode='lines+markers', name='Mediana', line=dict(color='gold', width=3), marker=dict(size=12)))

        fig.update_layout(
            title="Rozstrzał Oczekiwań FED co do Stóp Procentowych",
            xaxis_title="Rok Projekcji",
            yaxis_title="Stopa Procentowa (%)",
            xaxis=dict(tickmode='linear', dtick=1),
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Błąd pobierania danych z FRED: {e}")