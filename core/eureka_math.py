import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import t
try:
    from statsmodels.tsa.stattools import coint
except ImportError:
    coint = None

def compute_cointegration_zscore(series1, series2):
    """
    Computes the cointegration Z-Score for a pair of assets (StatArb).
    """
    if len(series1) < 30 or len(series2) < 30 or coint is None:
        return 0.0
    
    try:
        score, pvalue, _ = coint(series1, series2)
        spread = series1 - series2
        zscore = (spread.iloc[-1] - spread.mean()) / spread.std()
        return zscore if pvalue < 0.05 else 0.0
    except Exception:
        return 0.0

def compute_tail_dependence_copula(returns_df, dof=4):
    """
    Estimates the tail dependence penalty using a simplified Student-t Copula approach.
    High value means high systemic correlation (tail risk).
    """
    if len(returns_df) < 30:
        return 1.0
        
    corr_matrix = returns_df.corr(method='spearman')
    n = len(corr_matrix)
    if n <= 1: return 1.0
    avg_rho = (corr_matrix.sum().sum() - n) / (n * (n - 1))
    
    try:
        val = - np.sqrt( (dof + 1) * (1 - avg_rho) / (1 + avg_rho + 1e-6) )
        tail_dep = 2 * t.cdf(val, df=dof + 1)
        penalty = 1.0 + float(tail_dep)
    except Exception:
        penalty = 1.0
    return np.clip(penalty, 1.0, 3.0)

def compute_kelly_weights(returns_df, risk_free_rate=0.04, max_weight=0.35, copula_penalty=1.0, kelly_fraction=0.5):
    """
    Computes Fractional Kelly optimal portfolio weights based on modern portfolio theory.
    Optimizes for the maximum geometric growth rate while constrained to fully invested, long-only positions.
    kelly_fraction = 1.0 means Full Kelly, 0.5 means Half Kelly.
    """
    # Annualized mean returns and covariance
    mu = returns_df.mean() * 252
    cov = returns_df.cov() * 252
    
    n_assets = len(mu)
    r = risk_free_rate

    # Objective: Minimize negative Kelly growth rate
    def objective(w):
        port_return = np.dot(w, mu)
        port_var = np.dot(w.T, np.dot(cov, w))
        # Fractional Kelly corresponds to a risk aversion of 1 / kelly_fraction
        # Growth Rate for Fractional Kelly = (expected return) - (1 / (2 * kelly_fraction)) * variance
        variance_penalty = 0.5 / kelly_fraction
        growth = r + (port_return - r) - variance_penalty * port_var
        return -growth

    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    # Tighten concentration cap when systemic tail risk is high
    eff_cap = max_weight / copula_penalty
    bounds = tuple((0.0, eff_cap) for _ in range(n_assets))
    init_guess = np.ones(n_assets) / n_assets

    # Perform optimization
    res = minimize(objective, init_guess, bounds=bounds, constraints=constraints)
    
    if not res.success:
        # Fallback to equal weight if optimization fails to converge
        return {col: 1.0/n_assets for col in returns_df.columns}

    full_kelly = res.x
    
    # We return the constrained Kelly weights (which acts similarly to Half-Kelly 
    # since we do not allow leverage, dampening the absolute Kelly fractions).
    return dict(zip(returns_df.columns, full_kelly))

def compute_dynamic_regime_weights(current_vix, kelly_weights, universe=["SNXX", "SNDK", "SCHD"], crisis_anchor="SCHD", hmm_regime="BULL", iv_skew=1.0, macro_spread=1.0, is_macro_day=False, copula_penalty=1.0):
    """
    Blends the mathematically optimal Kelly weights with the Eureka safety mechanics,
    incorporating HMM Regimes, IV Skew, Macro Pulse, and Copula Tail Risk.
    """
    # Base VIX continuous Risk Factor: [0.0, 1.0]
    base_risk_factor = np.clip((current_vix - 15) / 15.0, 0.0, 1.0)
    
    # Adjust Risk Factor based on HMM Regime
    hmm_multiplier = {"BULL": 0.8, "NEUTRAL": 1.0, "BEAR": 1.5}.get(hmm_regime, 1.0)
    
    # Extreme Defense Triggers
    if iv_skew > 1.1 or macro_spread < 0 or is_macro_day or copula_penalty > 1.5:
        defense_mult = 3.0 if is_macro_day else 2.0
        defense_mult = max(defense_mult, copula_penalty)
        hmm_multiplier = max(hmm_multiplier, defense_mult)
        
    risk_factor = np.clip(base_risk_factor * hmm_multiplier * copula_penalty, 0.0, 1.0)
    
    # Crisis Anchor
    crisis = {tk: 0.0 for tk in universe}
    if crisis_anchor in crisis:
        crisis[crisis_anchor] = 1.0
    else:
        crisis[universe[-1]] = 1.0 # fallback to last asset
    
    # Interpolate between Kelly Optimality and Total Safety
    final_weights = {}
    for tk in universe:
        # If risk_factor is 0, we use 100% Kelly weights.
        # If risk_factor is 1, we use 100% Crisis weights (SCHD).
        w = (1 - risk_factor) * kelly_weights.get(tk, 0) + risk_factor * crisis.get(tk, 0)
        final_weights[tk] = w
        
    # Ensure they sum exactly to 1.0 (normalization)
    total = sum(final_weights.values())
    if total > 0:
        final_weights = {k: v / total for k, v in final_weights.items()}
        
    return final_weights

def compute_rsi(series, period=14):
    """
    Computes the Relative Strength Index (RSI).
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    # Replace infinities where loss is 0
    rs = rs.replace([np.inf, -np.inf], np.nan).fillna(100)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_vwap(df):
    """
    Computes the Volume Weighted Average Price (VWAP) for intraday data.
    Requires 'High', 'Low', 'Close', and 'Volume' columns.
    Typically, VWAP resets daily, but for a rolling window of a few hours,
    we can just compute the cumulative VWAP over the provided dataframe.
    """
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    cum_vol = df['Volume'].cumsum()
    cum_vol_price = (typical_price * df['Volume']).cumsum()
    vwap = cum_vol_price / cum_vol
    return vwap

