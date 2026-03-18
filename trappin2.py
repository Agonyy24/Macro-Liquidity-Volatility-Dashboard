import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime

# COS I TAK JEST ZLE Z TYM KODEM DALEJ WYKRYWA DRUGA SCIEZKE 

print("Pobieranie danych z rynku... To może chwilę potrwać.")

# --- KROK 1: POBIERANIE DANYCH ---
ticker_symbol = "SPY"
ticker = yf.Ticker(ticker_symbol)
spot_price = ticker.history(period="1d")['Close'].iloc[-1]
expirations = ticker.options

print(f"Obecna cena {ticker_symbol}: {spot_price:.2f}")

# Wybieramy kilka najbliższych terminów wygaśnięcia (np. od 2 do 8, żeby pominąć 0-DTE i mieć fajną strukturę)
selected_expirations = expirations[1:8]
today = datetime.today()

all_data = []

# --- KROK 2: CZYSZCZENIE I ZSZYWANIE OTM ---
for exp in selected_expirations:
    try:
        opt = ticker.option_chain(exp)
        calls = opt.calls
        puts = opt.puts
        
        # Liczymy Dni do Wygaśnięcia (DTE)
        exp_date = datetime.strptime(exp, '%Y-%m-%d')
        dte = (exp_date - today).days
        if dte <= 0: dte = 1 # Zabezpieczenie
        
        # ZŁOTA ZASADA: Bierzemy tylko Opcje Out-Of-The-Money (OTM)
        # OTM Puts: Strike < Spot (Lewe skrzydło)
        otm_puts = puts[puts['strike'] <= spot_price].copy()
        otm_puts['type'] = 'put'
        
        # OTM Calls: Strike > Spot (Prawe skrzydło)
        otm_calls = calls[calls['strike'] > spot_price].copy()
        otm_calls['type'] = 'call'
        
        # Łączymy w jeden czysty uśmiech dla danej daty
        clean_chain = pd.concat([otm_puts, otm_calls])
        
        # Dodatkowe filtry płynności i błędów (odrzucamy śmieci)
        clean_chain = clean_chain[
            (clean_chain['volume'] > 0) & 
            (clean_chain['impliedVolatility'] > 0.01) &
            (clean_chain['impliedVolatility'] < 1.5) # Odrzucamy ekstrema > 150% IV
        ]
        
        # Zapisujemy do głównej listy
        for _, row in clean_chain.iterrows():
            all_data.append([row['strike'], dte, row['impliedVolatility']])
            
    except Exception as e:
        print(f"Błąd przy dacie {exp}: {e}")

df = pd.DataFrame(all_data, columns=['Strike', 'DTE', 'IV'])

print(f"Zebrano {len(df)} czystych punktów OTM.")

# --- KROK 3: PRZYGOTOWANIE SIATKI 3D (INTERPOLACJA) ---
# Żeby Plotly narysowało gładką powierzchnię, musimy zamienić nasze kropki na gęstą siatkę
strike_grid = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
dte_grid = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
X, Y = np.meshgrid(strike_grid, dte_grid)

# Interpolujemy brakujące wartości (metoda 'cubic' daje najgładsze rezultaty)
Z = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='cubic')

# Zabezpieczenie przed krawędziami bez danych (wypełniamy najbliższą wartością, żeby wykres nie miał "dziur")
Z = np.nan_to_num(Z, nan=np.nanmean(Z))

# --- KROK 4: WIZUALIZACJA 3D ---
fig = go.Figure(data=[go.Surface(
    z=Z, x=X, y=Y, 
    colorscale='Plasma',
    colorbar_title='IV (Zmienność)'
)])

fig.update_layout(
    title=f"Powierzchnia Zmienności Implikowanej (IV Surface) dla {ticker_symbol}<br>Skonstruowana wyłącznie z płynnych opcji OTM",
    scene=dict(
        xaxis_title='Cena Wykonania (Strike)',
        yaxis_title='Dni do Wygaśnięcia (DTE)',
        zaxis_title='Implied Volatility (IV)',
        camera=dict(
            eye=dict(x=1.5, y=-1.5, z=0.5) # Domyślny kąt kamery
        )
    ),
    autosize=False,
    width=1000, height=800,
    margin=dict(l=65, r=50, b=65, t=90),
    template="plotly_dark"
)

# Zapisujemy do HTML, żeby obejść problem ładującego się serwera
filename = "iv_surface_3d.html"
fig.write_html(filename, auto_open=True)
print(f"Gotowe! Wykres zapisany i otwarty jako {filename}")