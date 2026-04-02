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
        
        # Szybsze i bezpieczniejsze pobieranie ceny spot
        try:
            spot_price = ticker.fast_info['lastPrice']
        except Exception:
            # Fallback w razie problemów z fast_info
            hist = ticker.history(period="5d")
            if hist.empty:
                return None, None, None, "Nie udało się pobrać ceny instrumentu bazowego."
            spot_price = hist['Close'].iloc[-1]
            
        expirations = ticker.options
        if not expirations:
            return None, None, None, "Brak danych o opcjach."

        # Pobieramy od indeksu 0 (nie omijamy najbliższych wygaśnięć!)
        selected_expirations = expirations[:10] 
        today = datetime.today().date() # Używamy samej daty dla czystej matematyki
        all_data = []

        for exp in selected_expirations:
            try:
                opt = ticker.option_chain(exp)
                calls = opt.calls
                puts = opt.puts
                
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                if dte <= 0: dte = 0.5 # 0.5 dnia dla opcji wygasających dzisiaj (0DTE)
                
                otm_puts = puts[puts['strike'] <= spot_price].copy()
                otm_calls = calls[calls['strike'] > spot_price].copy()
                
                clean_chain = pd.concat([otm_puts, otm_calls])
                
                # Dodano openInterest i podniesiono limit IV
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
            return None, None, None, "Filtry odrzuciły wszystkie opcje."

        df = pd.DataFrame(all_data, columns=['Strike', 'DTE', 'IV'])
        
        strike_grid = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
        dte_grid = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
        X, Y = np.meshgrid(strike_grid, dte_grid)
        
        # Dwustopniowa interpolacja eliminująca "płaskie klify"
        Z_linear = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='linear')
        Z_nearest = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='nearest')
        
        # Wypełniamy wartości NaN (krawędzie siatki) najbliższymi logicznymi punktami
        Z = np.where(np.isnan(Z_linear), Z_nearest, Z_linear)


        return X, Y, Z, spot_price, None
    except Exception as e:
        return None, None, None, None, str(e)

def render_iv_surface(ticker_symbol="SPY"):
    """Funkcja główna do wywołania w dashboardzie."""
    st.header(f"Implied Volatility Surface ({ticker_symbol})")
    st.markdown("Wykres zmontowany z płynnych opcji OTM (Out-of-the-Money). Pozwala ocenić *Term Structure* oraz *Volatility Skew*.")
    
    with st.spinner("Przeliczanie siatki 3D dla opcji (to zajmie kilka sekund)..."):
        # ZMIANA: Odbieramy dodatkową zmienną spot_price
        X, Y, Z, spot_price, error_msg = get_iv_surface_data(ticker_symbol)
        
        if error_msg:
            st.error(f"Nie udało się wygenerować powierzchni: {error_msg}")
        elif Z is not None:
            # Tworzymy główną powierzchnię IV
            fig_iv = go.Figure(data=[go.Surface(
                z=Z, x=X, y=Y, 
                colorscale='Plasma',
                colorbar_title='IV (Zmienność)'
            )])

            # --- NOWY KOD: Dodanie płaszczyzny dla ceny Spot (ATM) ---
            if spot_price:
                # Tworzymy siatkę dla pionowej ściany na całej wysokości Z i głębokości Y
                y_plane = np.array([Y.min(), Y.max()])
                z_plane = np.array([Z.min(), Z.max()])
                Y_plane, Z_plane = np.meshgrid(y_plane, z_plane)
                # Ustawiamy X na stałą wartość (aktualną cenę)
                X_plane = np.full_like(Y_plane, spot_price)

                fig_iv.add_trace(go.Surface(
                    x=X_plane, 
                    y=Y_plane, 
                    z=Z_plane,
                    colorscale=[[0, 'cyan'], [1, 'cyan']], # Jasnoniebieski kolor
                    opacity=0.4, # Półprzezroczysta, żeby nie zasłaniała danych
                    showscale=False, # Nie potrzebujemy dla niej legendy
                    name='Spot Price (ATM)',
                    hoverinfo='skip' # Żeby myszka nie "łapała" tej ściany
                ))
            # ---------------------------------------------------------

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