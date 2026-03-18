import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
from datetime import datetime

# --- KROK 1: POBIERANIE DANYCH ---
ticker = yf.Ticker("SPY")
spot_price = ticker.history(period="1d")['Close'].iloc[-1]
expirations = ticker.options

# Wybieramy opcje, które wygasają za około miesiąc (unikamy opcji 0-DTE ze względu na szum)
target_exp = expirations[3] 
opt = ticker.option_chain(target_exp)
calls = opt.calls

# Liczymy czas do wygaśnięcia (T) w latach
today = datetime.today()
exp_date = datetime.strptime(target_exp, '%Y-%m-%d')
dte = (exp_date - today).days
T = dte / 365.0
r = 0.05 # Zakładamy stopę wolną od ryzyka na poziomie 5%

# --- KROK 2: CZYSZCZENIE DANYCH ---
# Interesuje nas tylko zakres wokół obecnej ceny (np. +/- 15%) i opcje płynne
lower_bound = spot_price * 0.85
upper_bound = spot_price * 1.15

filtered_calls = calls[
    (calls['strike'] >= lower_bound) & 
    (calls['strike'] <= upper_bound) & 
    (calls['volume'] > 0) &              # Odrzucamy opcje, którymi nikt nie handluje
    (calls['impliedVolatility'] > 0.01)  # Odrzucamy błędy Yahoo Finance
].copy()

# Wyciągamy wyczyszczone Strike'i i IV
strikes = filtered_calls['strike'].values
ivs = filtered_calls['impliedVolatility'].values

print(f"Pobrano {len(strikes)} przefiltrowanych opcji. Obecna cena SPY: {spot_price:.2f}")

if len(strikes) < 3:
    print("BŁĄD: Za mało danych opcyjnych, żeby wyrysować krzywą! Zmień termin wygaśnięcia.")

# --- KROK 2.5: WIZUALIZACJA SUROWYCH PUNKTÓW (STRIKE VS IV) ---
# Tworzymy osobny wykres tylko dla kropek
fig_raw = go.Figure()

fig_raw.add_trace(go.Scatter(
    x=strikes, 
    y=ivs, 
    mode='markers', # 'markers' oznacza, że rysujemy same kropki, bez łączenia ich linią
    name='Surowe punkty IV z rynku',
    marker=dict(color='orange', size=8, opacity=0.8)
))

# Dodajemy pionową linię pokazującą, gdzie obecnie znajduje się cena akcji (SPOT)
fig_raw.add_vline(
    x=spot_price, line_width=2, line_dash="dash", line_color="red", 
    annotation_text=f"Obecna cena ({spot_price:.2f})"
)

fig_raw.update_layout(
    title=f"Surowe Dane Giełdowe: Zmienność Implikowana (IV) dla SPY",
    xaxis_title="Cena Wykonania (Strike)",
    yaxis_title="Zmienność Implikowana (IV)",
    template="plotly_dark"
)

# Zapisujemy do pliku i otwieramy w przeglądarce
fig_raw.write_html("surowe_dane_IV.html", auto_open=True)
print("Wygenerowano plik: surowe_dane_IV.html")

# --- KROK 3: WYGŁADZANIE (FITOWANIE KRZYWEJ) ---
# Zamiast łączyć punkty rynkowe (które mają szum), dopasowujemy wielomian 2. stopnia (parabolę),
# aby uzyskać gładki "Uśmiech Zmienności"
poly_coefs = np.polyfit(strikes, ivs, deg=2)
smooth_iv_func = np.poly1d(poly_coefs)

# Tworzymy bardzo gęstą siatkę Strike'ów (np. 500 punktów co kilka centów)
dense_strikes = np.linspace(strikes.min(), strikes.max(), 500)
smooth_ivs = smooth_iv_func(dense_strikes)

# Funkcja Blacka-Scholesa, żeby zamienić z powrotem gładkie IV na gładkie ceny Opcji Call
def black_scholes_call(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

# Liczymy gładkie, teoretyczne ceny (C_K)
smooth_calls = black_scholes_call(spot_price, dense_strikes, T, r, smooth_ivs)

# --- KROK 4: BREEDEN-LITZENBERGER (DRUGA POCHODNA) ---
dK = dense_strikes[1] - dense_strikes[0] # Nasz krok \Delta K
rnd = np.zeros_like(smooth_calls)

# Pętla licząca nieskończenie małego "Motyla" (różnica centralna dla 2. pochodnej)
# f(K) = exp(rT) * (C[i+1] - 2*C[i] + C[i-1]) / dK^2
for i in range(1, len(smooth_calls) - 1):
    butterfly_cost = smooth_calls[i+1] - 2 * smooth_calls[i] + smooth_calls[i-1]
    rnd[i] = np.exp(r * T) * butterfly_cost / (dK ** 2)

# Odrzucamy pierwszy i ostatni punkt (bo tam pochodna nie miała pełnych danych)
plot_strikes = dense_strikes[1:-1]
plot_rnd = rnd[1:-1]

# --- KROK 5: WIZUALIZACJA ---
fig = go.Figure()

# Wykres gęstości (Risk-Neutral Density)
fig.add_trace(go.Scatter(
    x=plot_strikes, y=plot_rnd, 
    mode='lines', 
    name='Implikowany Rozkład Prawdopodobieństwa (RND)',
    line=dict(color='blue', width=3),
    fill='tozeroy'
))

# Linia pokazująca obecną cenę SPOT
fig.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="red", 
              annotation_text=f"Obecna cena ({spot_price:.2f})")

fig.update_layout(
    title=f"Rynkowe Oczekiwania co do ceny SPY (Wygaśnięcie: {target_exp})",
    xaxis_title="Cena SPY (Strike)",
    yaxis_title="Gęstość Prawdopodobieństwa",
    template="plotly_dark"
)

# --- ZMIANA TUTAJ ---
# Zamiast fig.show() (które stawia serwer), zapisujemy do pliku:
fig.write_html("moj_wykres_RND.html", auto_open=True)

# Alternatywnie, jeśli wolisz fig.show(), możesz wymusić otwarcie w przeglądarce:
# fig.show(renderer="browser")