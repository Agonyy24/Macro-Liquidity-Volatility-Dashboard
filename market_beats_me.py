import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime

# 1. Pobieranie danych
ticker = yf.Ticker("SPY")
spot_price = ticker.history(period="1d")['Close'].iloc[-1]
expirations = ticker.options

# Filtrujemy tylko opcje krótkoterminowe (np. najbliższe 5-6 terminów)
short_term_expirations = expirations[:6]

data = []
today = datetime.today()

for exp in short_term_expirations:
    opt = ticker.option_chain(exp)
    calls = opt.calls
    
    # Czas do wygaśnięcia w dniach
    exp_date = datetime.strptime(exp, '%Y-%m-%d')
    dte = (exp_date - today).days
    if dte <= 0: dte = 1 # Zabezpieczenie przed błędem zera
    
    # Wybieramy opcje w okolicach kursu obecnego (At-The-Money +/- 10%)
    lower_bound = spot_price * 0.90
    upper_bound = spot_price * 1.10
    calls = calls[(calls['strike'] >= lower_bound) & (calls['strike'] <= upper_bound)]
    
    for _, row in calls.iterrows():
        # Yahoo Finance często podaje gotowe impliedVolatility
        if row['impliedVolatility'] > 0:
            data.append([row['strike'], dte, row['impliedVolatility']])

df = pd.DataFrame(data, columns=['Strike', 'DTE', 'IV'])

# 2. Przygotowanie danych do wykresu 3D (Interpolacja)
# Plotly Surface potrzebuje siatki (mesh grid)
strikes = np.linspace(df['Strike'].min(), df['Strike'].max(), 50)
dtes = np.linspace(df['DTE'].min(), df['DTE'].max(), 50)
X, Y = np.meshgrid(strikes, dtes)

# Interpolujemy brakujące punkty zmienności implikowanej
Z = griddata((df['Strike'], df['DTE']), df['IV'], (X, Y), method='cubic')
# Zabezpieczenie przed nan (wypełniamy najbliższymi wartościami)
Z = np.nan_to_num(Z, nan=np.nanmean(Z))

# 3. Modelowanie płaszczyzny 3D w Plotly
fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Viridis')])

fig.update_layout(
    title='Powierzchnia Zmienności Implikowanej (SPY Opcje Krótkoterminowe)',
    scene=dict(
        xaxis_title='Cena Wykonania (Strike)',
        yaxis_title='Dni do wygaśnięcia (DTE)',
        zaxis_title='Zmienność Implikowana (IV)'
    ),
    autosize=False,
    width=900, height=700,
    margin=dict(l=65, r=50, b=65, t=90)
)

fig.show()