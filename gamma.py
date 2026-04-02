import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from scipy.stats import norm
import streamlit as st

# --- Funkcja pomocnicza: Wyliczanie Gammy ---
def calc_gamma(S, K, T, r, sigma):
    # Zabezpieczenie przed błędem dzielenia przez zero dla bardzo krótkich opcji
    T = np.maximum(T, 1e-5)
    sigma = np.maximum(sigma, 1e-5)
    
    # Wzór Blacka-Scholesa na d1
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    # Gamma to pochodna z d1
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return gamma

# --- Główny komponent Dashboardu ---
def plot_gamma_profile():
    st.subheader("Profil Ekspozycji na Gammę (Net GEX)")
    
    # Dodajemy suwak DTE na samej górze interfejsu
    max_dte = st.slider("Filtruj opcje do ilu dni w przód (max DTE)?", min_value=0, max_value=90, value=7)
    
    with st.spinner('Klonowanie portfeli Market Makerów (wyliczanie Gammy)...'):
        try:
            ticker = yf.Ticker("SPY")
            spot_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Pobieramy więcej terminów wygaśnięcia (np. 15), żeby suwak miał z czego filtrować dane
            expirations = ticker.options[:15] 
            
            gex_data = []
            
            for exp in expirations:
                # Używamy .normalize() aby pozbyć się godzin i mieć czyste porównanie dni
                today_date = pd.Timestamp.today().normalize()
                exp_date = pd.to_datetime(exp).normalize()
                days_to_exp = (exp_date - today_date).days
                
                # --- INTEGRACJA SUWAKA ---
                # Jeśli opcja wygasa później niż wskazuje suwak, całkowicie ją pomijamy w obliczeniach
                if days_to_exp > max_dte:
                    continue
                
                # Zabezpieczenie przed dzieleniem przez zero.
                # Jeśli opcja wygasa dzisiaj (0 dni), sztucznie zakładamy minimum 0.5 dnia
                # aby Gamma nie wystrzeliła w nieskończoność (Dirac Delta).
                T = max(days_to_exp, 0.5) / 365.0
                
                opt = ticker.option_chain(exp)
                
                # --- Opcje CALL ---
                calls = opt.calls
                # Ręcznie liczymy Gammę dla każdej opcji w łańcuchu
                calls['Gamma'] = calc_gamma(spot_price, calls['strike'], T, 0.04, calls['impliedVolatility'])
                # GEX = Open Interest * Gamma * Mnożnik (100) * Obecna Cena
                calls['GEX'] = calls['openInterest'] * calls['Gamma'] * 100 * spot_price
                
                # --- Opcje PUT ---
                puts = opt.puts
                puts['Gamma'] = calc_gamma(spot_price, puts['strike'], T, 0.04, puts['impliedVolatility'])
                # Tradycyjnie zakładamy, że klienci kupują Puty ubezpieczeniowe, więc dla Market Makera to ujemna ekspozycja
                puts['GEX'] = -puts['openInterest'] * puts['Gamma'] * 100 * spot_price
                
                # Zapisujemy wyliczenia
                gex_data.append(calls[['strike', 'GEX']])
                gex_data.append(puts[['strike', 'GEX']])
                
            # Łączymy całą tabelę i sumujemy GEX dla każdego poziomu ceny (Strike)
            df_gex = pd.concat(gex_data)
            gex_profile = df_gex.groupby('strike')['GEX'].sum().reset_index()
            
            # Filtrujemy tylko najbliższe poziomy (+/- 10% od obecnej ceny), żeby odciąć szum i skupić się na akcji
            gex_profile = gex_profile[(gex_profile['strike'] > spot_price * 0.9) & (gex_profile['strike'] < spot_price * 1.1)]

            # --- Rysowanie wykresu ---
            fig = go.Figure()
            
            # Kolorujemy słupki: Zielone (dodatnie GEX - amortyzator), Czerwone (ujemne GEX - przyspieszenie)
            colors = ['red' if val < 0 else 'green' for val in gex_profile['GEX']]
            
            fig.add_trace(go.Bar(
                x=gex_profile['strike'],
                y=gex_profile['GEX'],
                marker_color=colors,
                name='Net GEX'
            ))
            
            # Zaznaczamy, gdzie SPY znajduje się w tym momencie
            fig.add_vline(
                x=spot_price, 
                line_dash="dash", 
                line_color="gold", 
                annotation_text=f" Obecna cena SPY: {spot_price:.2f}",
                annotation_position="top left"
            )

            fig.update_layout(
                title="Profil Net GEX dla S&P 500 (Gdzie są opcyjne ściany?)",
                xaxis_title="Poziom Cenowy (Strike)",
                yaxis_title="Ekspozycja na Gammę (Wielkość Ściany)",
                template="plotly_dark",
                bargap=0.2
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Wystąpił błąd podczas obliczania GEX: {e}")