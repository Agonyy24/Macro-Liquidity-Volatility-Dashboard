# src/gamma_exposure.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from scipy.stats import norm
import streamlit as st

@st.cache_data(ttl=86400)  # Refresh once per day - rate doesn't change very often
def get_risk_free_rate(_fred) -> float:
    try:
        # DGS3MO = 3-Month Bond
        series = _fred.get_series("DGS3MO")
        rate_pct = series.dropna().iloc[-1]
        return float(rate_pct) / 100.0  # Convert from percent to decimal

    except Exception as e:
        st.warning(f"Could not fetch risk-free rate from FRED ({e}). Falling back to 4.0%.")
        return 0.04


# --- Black-Scholes Gamma calculation ---
def calc_gamma(S: float, K: pd.Series, T: float, r: float, sigma: pd.Series) -> pd.Series:
    """
    Computes Black-Scholes gamma for a series of options.

    Args:
        S:     Current spot price of the underlying asset.
        K:     Series of strike prices.
        T:     Time to expiration in years.
        r:     Risk-free interest rate (decimal, e.g. 0.045).
        sigma: Series of implied volatilities (decimal).

    Returns:
        Series of gamma values (second derivative of option price w.r.t. spot).
    """
    # Protect from division by zero
    T = np.maximum(T, 1e-5)
    sigma = np.maximum(sigma, 1e-5)

    # d1 from the Black-Scholes formula
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    # Gamma = N'(d1) / (S * sigma * sqrt(T))
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return gamma


# --- Main Streamlit component ---

def plot_gamma_profile(fred, ticker_symbol: str = "SPY") -> None:
    """
    Renders the Net Gamma Exposure (GEX) bar chart inside a Streamlit dashboard.
    IMPORTANT: This function assumes market makers are short on calls and long on puts.
    Positive GEX = acts as a volatility suppressor (Call Walls).
    Negative GEX = acts as a volatility accelerator (Put Walls).
    """
    st.subheader(f"Net Gamma Exposure (GEX) Profile - {ticker_symbol}")
    st.markdown(
        "<span style='font-size:14px; color:gray;'>"
        "Market Maker hedging levels. "
        "Positive = Volatility suppression (Call Walls). "
        "Negative = Volatility acceleration (Put Walls)."
        "</span>",
        unsafe_allow_html=True,
    )

    # --- UI Controls ---
    max_dte = st.slider(
        "Filter options by max Days to Expiry (DTE)",
        min_value=0,
        max_value=90,
        value=7,
    )

    with st.spinner("Fetching risk-free rate and calculating Gamma Exposure..."):
        try:
            r = get_risk_free_rate(fred)

            # --- Spot Price ---
            ticker = yf.Ticker(ticker_symbol)
            try:
                spot_price = ticker.fast_info["lastPrice"]
            except Exception:
                spot_price = ticker.history(period="1d")["Close"].iloc[-1]

            # Fetch the first 15 expirations from the options chain
            expirations = ticker.options[:15]

            gex_rows = []
            today = pd.Timestamp.today().normalize()

            for exp in expirations:
                exp_date = pd.to_datetime(exp).normalize()
                days_to_exp = (exp_date - today).days

                # Skip expirations beyond the user-selected DTE threshold
                if days_to_exp > max_dte:
                    continue

                # Treat 0-DTE options as having 0.5 days left to avoid singularity
                T = max(days_to_exp, 0.5) / 365.0

                chain = ticker.option_chain(exp)

                # --- Call options ---
                calls = chain.calls.copy()
                calls["Gamma"] = calc_gamma(
                    spot_price, calls["strike"], T, r, calls["impliedVolatility"]
                )
                calls["GEX"] = calls["openInterest"] * calls["Gamma"] * 100 * spot_price

                # --- Put options ---
                puts = chain.puts.copy()
                puts["Gamma"] = calc_gamma(
                    spot_price, puts["strike"], T, r, puts["impliedVolatility"]
                )
                puts["GEX"] = -puts["openInterest"] * puts["Gamma"] * 100 * spot_price

                gex_rows.append(calls[["strike", "GEX"]])
                gex_rows.append(puts[["strike", "GEX"]])

            if not gex_rows:
                st.warning("No options data found within the selected DTE range.")
                return

            # Aggregate GEX per strike across all selected expirations
            df_gex = pd.concat(gex_rows, ignore_index=True)
            gex_profile = df_gex.groupby("strike")["GEX"].sum().reset_index()

            # Restrict to strikes within ±10% of spot to remove far-OTM noise
            gex_profile = gex_profile[
                (gex_profile["strike"] > spot_price * 0.90)
                & (gex_profile["strike"] < spot_price * 1.10)
            ]

            # --- Chart ---
            colors = [
                "#e05252" if val < 0 else "#26a641"
                for val in gex_profile["GEX"]
            ]

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=gex_profile["strike"],
                    y=gex_profile["GEX"],
                    marker_color=colors,
                    name="Net GEX",
                    hovertemplate=(
                        "<b>Strike:</b> %{x}<br>"
                        "<b>Net GEX:</b> %{y:,.0f}"
                        "<extra></extra>"
                    ),
                )
            )

            # Vertical line at current spot price
            fig.add_vline(
                x=spot_price,
                line_dash="dash",
                line_color="gold",
                annotation_text=f" Spot: {spot_price:.2f} | r: {r:.2%}",
                annotation_position="top left",
                annotation_font=dict(color="gold"),
            )

            fig.update_layout(
                xaxis_title="Strike Price",
                yaxis_title="Gamma Exposure (Wall Size)",
                template="plotly_dark",
                bargap=0.2,
                height=500,
                margin=dict(l=0, r=0, t=30, b=0),
                showlegend=False,
            )

            st.plotly_chart(fig, width='stretch')

        except Exception as e:
            st.error(f"Error calculating GEX: {e}")