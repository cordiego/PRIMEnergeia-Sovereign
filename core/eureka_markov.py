"""
EUREKA SOVEREIGN — Markov Day Chain Module
============================================
2-state (Green/Red) Markov chain for daily return sequences.
Detects trending vs choppy regimes, computes streak distributions,
gap-conditioned probabilities, and decay-adjusted expected returns.

PRIMEnergeia S.A.S.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("eureka.markov")

# ────────────────────────────────────────────────────────────
#  MARKOV DAY CHAIN
# ────────────────────────────────────────────────────────────

GREEN, RED = 0, 1
STATE_LABELS = {GREEN: "GREEN", RED: "RED"}


class MarkovDayChain:
    """2-state (Green/Red) Markov chain for daily return sequences."""

    def __init__(self):
        # Transition matrix: P[i][j] = P(state_j | state_i)
        # Row 0 = from GREEN, Row 1 = from RED
        self.transition_matrix = np.array([[0.5, 0.5],
                                           [0.5, 0.5]])
        self.states = np.array([])           # full state sequence
        self.returns = pd.Series(dtype=float)
        self.green_streaks = {}              # length -> count
        self.red_streaks = {}                # length -> count
        self._fitted = False

    # ── FIT ──────────────────────────────────────────────────

    def fit(self, daily_returns: pd.Series, min_periods: int = 60):
        """
        Build transition matrix from daily returns.
        Green = return >= 0, Red = return < 0.
        """
        dr = daily_returns.dropna()
        if len(dr) < min_periods:
            logger.warning(f"Only {len(dr)} data points (need {min_periods}). Using uniform priors.")
            self._fitted = True
            return self

        self.returns = dr
        self.states = np.where(dr.values >= 0, GREEN, RED)

        # Build transition counts
        counts = np.zeros((2, 2), dtype=float)
        for i in range(len(self.states) - 1):
            counts[self.states[i], self.states[i + 1]] += 1

        # Normalize rows
        for row in range(2):
            row_sum = counts[row].sum()
            if row_sum > 0:
                self.transition_matrix[row] = counts[row] / row_sum

        # Build streak distributions
        self.green_streaks, self.red_streaks = self._compute_streaks(self.states)

        self._fitted = True
        logger.info(
            f"Markov chain fitted on {len(dr)} days. "
            f"P(G->G)={self.transition_matrix[GREEN, GREEN]:.3f}  "
            f"P(R->R)={self.transition_matrix[RED, RED]:.3f}"
        )
        return self

    # ── REGIME DETECTION ─────────────────────────────────────

    def get_regime(self, window: int = 20) -> str:
        """
        Detect if the trailing `window` transitions are TRENDING or CHOPPY.

        CHOPPY  = alternating days (P(G->R) > 0.55 AND P(R->G) > 0.55)
        TRENDING = persistence       (P(G->G) > 0.55 OR P(R->R) > 0.55)
        NEUTRAL = otherwise
        """
        if len(self.states) < window + 1:
            return "NEUTRAL"

        tail = self.states[-(window + 1):]
        counts = np.zeros((2, 2), dtype=float)
        for i in range(len(tail) - 1):
            counts[tail[i], tail[i + 1]] += 1

        p = np.zeros((2, 2))
        for row in range(2):
            row_sum = counts[row].sum()
            if row_sum > 0:
                p[row] = counts[row] / row_sum
            else:
                p[row] = [0.5, 0.5]

        p_gr = p[GREEN, RED]
        p_rg = p[RED, GREEN]
        p_gg = p[GREEN, GREEN]
        p_rr = p[RED, RED]

        if p_gr > 0.55 and p_rg > 0.55:
            return "CHOPPY"
        elif p_gg > 0.55 or p_rr > 0.55:
            return "TRENDING"
        else:
            return "NEUTRAL"

    # ── PREDICTION ───────────────────────────────────────────

    def predict_next_day(self) -> dict:
        """
        Given the current state (last day green or red), return
        transition probabilities for tomorrow.
        """
        if len(self.states) == 0:
            return {
                "p_green": 0.5, "p_red": 0.5,
                "current_state": "UNKNOWN", "regime": "NEUTRAL"
            }

        current = self.states[-1]
        return {
            "p_green": float(self.transition_matrix[current, GREEN]),
            "p_red":   float(self.transition_matrix[current, RED]),
            "current_state": STATE_LABELS[current],
            "regime": self.get_regime()
        }

    # ── STREAK ANALYSIS ──────────────────────────────────────

    def streak_analysis(self) -> dict:
        """Full streak statistics for the fitted chain."""
        if len(self.states) == 0:
            return {
                "current_streak_length": 0,
                "current_streak_direction": "UNKNOWN",
                "avg_green_streak": 0.0, "avg_red_streak": 0.0,
                "max_green_streak": 0, "max_red_streak": 0,
                "green_streak_dist": {}, "red_streak_dist": {}
            }

        # Current streak
        current_dir = self.states[-1]
        streak_len = 1
        for i in range(len(self.states) - 2, -1, -1):
            if self.states[i] == current_dir:
                streak_len += 1
            else:
                break

        def _avg_streak(dist):
            if not dist:
                return 0.0
            total = sum(l * c for l, c in dist.items())
            count = sum(dist.values())
            return total / count if count > 0 else 0.0

        return {
            "current_streak_length": streak_len,
            "current_streak_direction": STATE_LABELS[current_dir],
            "avg_green_streak": _avg_streak(self.green_streaks),
            "avg_red_streak":   _avg_streak(self.red_streaks),
            "max_green_streak": max(self.green_streaks.keys(), default=0),
            "max_red_streak":   max(self.red_streaks.keys(), default=0),
            "green_streak_dist": dict(self.green_streaks),
            "red_streak_dist":   dict(self.red_streaks),
        }

    # ── GAP-CONDITIONED PROBABILITY ──────────────────────────

    def conditional_gap_probability(
        self,
        daily_returns: pd.Series,
        daily_opens: pd.Series,
        daily_prev_closes: pd.Series
    ) -> dict:
        """
        Compute P(Green | gap bin) from historical data.
        Bins: large_negative (<-1%), small_negative (-1% to 0%),
              small_positive (0% to +1%), large_positive (>+1%).
        """
        gap_pct = (daily_opens - daily_prev_closes) / daily_prev_closes
        green = daily_returns >= 0

        # Align indices
        common = gap_pct.dropna().index.intersection(green.dropna().index)
        gap_pct = gap_pct.loc[common]
        green = green.loc[common]

        bins = {
            "large_negative":  gap_pct < -0.01,
            "small_negative": (gap_pct >= -0.01) & (gap_pct < 0),
            "small_positive": (gap_pct >= 0) & (gap_pct < 0.01),
            "large_positive":  gap_pct >= 0.01,
        }

        result = {}
        for label, mask in bins.items():
            subset = green[mask]
            if len(subset) > 0:
                result[label] = float(subset.mean())
            else:
                result[label] = 0.5  # prior
        return result

    # ── ROLLING TRANSITION MATRIX ────────────────────────────

    def rolling_transition_matrix(self, window: int = 20) -> pd.DataFrame:
        """
        Time-varying transition matrix over a rolling window.
        Returns a DataFrame with columns:
            date, p_gg, p_gr, p_rg, p_rr, regime
        """
        if len(self.states) < window + 1 or len(self.returns) < window + 1:
            return pd.DataFrame(columns=["date", "p_gg", "p_gr", "p_rg", "p_rr", "regime"])

        rows = []
        dates = self.returns.index

        for end in range(window, len(self.states)):
            seg = self.states[end - window:end + 1]
            counts = np.zeros((2, 2), dtype=float)
            for i in range(len(seg) - 1):
                counts[seg[i], seg[i + 1]] += 1

            p = np.zeros((2, 2))
            for r in range(2):
                rs = counts[r].sum()
                p[r] = counts[r] / rs if rs > 0 else [0.5, 0.5]

            p_gg = p[GREEN, GREEN]
            p_gr = p[GREEN, RED]
            p_rg = p[RED, GREEN]
            p_rr = p[RED, RED]

            if p_gr > 0.55 and p_rg > 0.55:
                regime = "CHOPPY"
            elif p_gg > 0.55 or p_rr > 0.55:
                regime = "TRENDING"
            else:
                regime = "NEUTRAL"

            rows.append({
                "date": dates[end],
                "p_gg": float(p_gg), "p_gr": float(p_gr),
                "p_rg": float(p_rg), "p_rr": float(p_rr),
                "regime": regime,
            })

        return pd.DataFrame(rows)

    # ── DECAY-ADJUSTED EXPECTED RETURN ───────────────────────

    def decay_adjusted_expected_return(
        self,
        base_return: float,
        realized_vol_5d: float,
        decay_lambda: float = 0.002250
    ) -> float:
        """
        Estimate today's expected return for SNXX adjusting for
        volatility decay under the current regime.

        CHOPPY:   decay amplified x2.0 (leverage hurts)
        TRENDING: decay minimal  x0.5 (leverage helps)
        NEUTRAL:  standard       x1.0
        """
        regime = self.get_regime()
        multiplier = {"CHOPPY": 2.0, "TRENDING": 0.5, "NEUTRAL": 1.0}.get(regime, 1.0)
        decay_cost = decay_lambda * (realized_vol_5d ** 2) * multiplier
        return base_return - decay_cost

    # ── INTERNAL HELPERS ─────────────────────────────────────

    @staticmethod
    def _compute_streaks(states: np.ndarray):
        """Compute streak length distributions for green and red days."""
        green_dist = {}
        red_dist = {}

        if len(states) == 0:
            return green_dist, red_dist

        current_val = states[0]
        current_len = 1

        for i in range(1, len(states)):
            if states[i] == current_val:
                current_len += 1
            else:
                dist = green_dist if current_val == GREEN else red_dist
                dist[current_len] = dist.get(current_len, 0) + 1
                current_val = states[i]
                current_len = 1

        # Record the final streak
        dist = green_dist if current_val == GREEN else red_dist
        dist[current_len] = dist.get(current_len, 0) + 1

        return green_dist, red_dist

    def __repr__(self):
        if not self._fitted:
            return "MarkovDayChain(not fitted)"
        sa = self.streak_analysis()
        return (
            f"MarkovDayChain(n={len(self.states)}, "
            f"P(G->G)={self.transition_matrix[GREEN, GREEN]:.3f}, "
            f"P(R->R)={self.transition_matrix[RED, RED]:.3f}, "
            f"regime={self.get_regime()}, "
            f"streak={sa['current_streak_length']}{sa['current_streak_direction'][0]})"
        )


# ────────────────────────────────────────────────────────────
#  CONVENIENCE BUILDER
# ────────────────────────────────────────────────────────────

def build_full_history_chain(ticker: str = "SNDK") -> MarkovDayChain:
    """
    Download ALL available history for ticker and build the Markov chain.
    Uses yfinance period='max' for maximum lookback.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance is required. Install with: pip install yfinance")
        return MarkovDayChain()

    logger.info(f"Downloading full history for {ticker}...")
    try:
        df = yf.download(ticker, period="max", progress=False)
        if df.empty:
            logger.warning(f"No data returned for {ticker}.")
            return MarkovDayChain()

        if isinstance(df.columns, pd.MultiIndex):
            closes = df["Close"].iloc[:, 0]
        else:
            closes = df["Close"]

        daily_returns = closes.pct_change().dropna()
        logger.info(f"Fetched {len(daily_returns)} trading days for {ticker} "
                     f"({daily_returns.index[0].strftime('%Y-%m-%d')} -> "
                     f"{daily_returns.index[-1].strftime('%Y-%m-%d')})")

        chain = MarkovDayChain()
        chain.fit(daily_returns, min_periods=30)
        return chain

    except Exception as e:
        logger.error(f"Failed to build chain for {ticker}: {e}")
        return MarkovDayChain()
