"""
PRIMEnergeia — Data Upload & Quality Dashboard
=================================================
Provides:
  1. File uploader for client CSV data
  2. Auto-detection of market format
  3. Data quality report (completeness, price distribution, anomalies)
  4. Session state persistence for cross-page data sharing

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys
import tempfile

# Ensure project root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from data.data_loader import load_dataset, detect_encoding, DataQualityReport

# ─── Page Header ────────────────────────────────────────────
st.markdown("# 📂 Data Upload & Quality Report")
st.caption("UPLOAD · VALIDATE · ANALYZE — Guaranteed Data Integrity")
st.divider()

# ─── File Uploader ──────────────────────────────────────────
st.markdown("### Upload Market Data")
st.markdown(
    "Upload your CSV file. PRIMEnergeia will auto-detect the market format "
    "(ERCOT, SEN/CENACE, MIBEL/OMIE) and validate data quality."
)

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Supported formats: ERCOT (dam_lmp, rtm_lmp), SEN (Actual_MW, Theoretical_MW, PML_USD)",
    )
with col2:
    market_override = st.selectbox(
        "Market (optional)",
        ["Auto-detect", "ERCOT", "SEN", "MIBEL"],
        help="Leave on Auto-detect unless your file uses non-standard column names",
    )
    node_id = st.text_input(
        "SEN Node ID (optional)",
        value="07-HER-230",
        help="Only needed for SEN nodo format files",
    )

# ─── Load Default Data ──────────────────────────────────────
st.markdown("---")
st.markdown("### Or Load Default Dataset")
default_cols = st.columns(3)
with default_cols[0]:
    if st.button("🇺🇸 ERCOT Historical", use_container_width=True):
        try:
            ds = load_dataset(market="ercot")
            st.session_state["prime_dataset"] = ds
            st.session_state["prime_data_source"] = "ERCOT Historical (default)"
            st.success(f"Loaded ERCOT: {ds.hours} intervals")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")

with default_cols[1]:
    if st.button("🇲🇽 SEN Node 07-HER-230", use_container_width=True):
        try:
            ds = load_dataset(market="sen", node_id="07-HER-230")
            st.session_state["prime_dataset"] = ds
            st.session_state["prime_data_source"] = "SEN 07-HER-230 (default)"
            st.success(f"Loaded SEN: {ds.hours} intervals")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")

with default_cols[2]:
    if st.button("🔄 Clear Data", use_container_width=True, type="secondary"):
        if "prime_dataset" in st.session_state:
            del st.session_state["prime_dataset"]
            del st.session_state["prime_data_source"]
        st.info("Data cleared")
        st.rerun()

# ─── Process Uploaded File ──────────────────────────────────
if uploaded is not None:
    # Write to temp file for data_loader
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='wb') as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    try:
        market = None if market_override == "Auto-detect" else market_override.lower()
        nid = node_id if market == "sen" else None

        ds = load_dataset(market=market, filepath=tmp_path, node_id=nid)
        st.session_state["prime_dataset"] = ds
        st.session_state["prime_data_source"] = f"Uploaded: {uploaded.name}"
        st.success(f"✅ Loaded {ds.hours} intervals from `{uploaded.name}` (market: {ds.market})")
    except Exception as e:
        st.error(f"❌ Failed to load `{uploaded.name}`")
        st.markdown(f"**Error:** `{e}`")
        st.info(
            "**Tips:**\n"
            "- Check that your CSV has headers matching one of the supported formats\n"
            "- Try selecting a specific market instead of Auto-detect\n"
            "- Run `python preflight.py your_file.csv` for detailed diagnostics"
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# ─── Display Quality Report ────────────────────────────────
if "prime_dataset" in st.session_state:
    ds = st.session_state["prime_dataset"]
    source = st.session_state.get("prime_data_source", "Unknown")

    st.divider()
    st.markdown(f"### 📊 Data Quality Report — `{source}`")

    # Metrics row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("INTERVALS", f"{ds.hours:,}")
    m2.metric("MARKET", ds.market.upper())

    if ds.quality:
        m3.metric("COMPLETENESS", f"{ds.quality.completeness_pct}%")
        m4.metric("SKIPPED", f"{ds.quality.skipped_rows}")
        date_range = f"{ds.quality.date_range[0][:10]} → {ds.quality.date_range[1][:10]}"
        m5.metric("DATE RANGE", date_range)

    # Price distribution
    st.markdown("#### Price Distribution")
    col_a, col_b = st.columns(2)

    with col_a:
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=ds.da_prices,
            name="DA/PML Prices",
            marker_color="#00d1ff",
            opacity=0.7,
            nbinsx=50,
        ))
        if not np.allclose(ds.da_prices, ds.rt_prices):
            fig_hist.add_trace(go.Histogram(
                x=ds.rt_prices,
                name="RT Prices",
                marker_color="#ff6b35",
                opacity=0.5,
                nbinsx=50,
            ))
        fig_hist.update_layout(
            title="Price Distribution",
            xaxis_title="Price ($/MWh)",
            yaxis_title="Frequency",
            template="plotly_dark",
            paper_bgcolor="#050810",
            plot_bgcolor="#0a0f1a",
            barmode="overlay",
            height=350,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_b:
        # Stats table
        stats_data = {
            "Metric": ["Mean", "Median", "Std Dev", "Min", "Max",
                        "Spike Hours (>$200)", "Negative Hours"],
            "DA/PML Price": [
                f"${np.nanmean(ds.da_prices):.2f}",
                f"${np.nanmedian(ds.da_prices):.2f}",
                f"${np.nanstd(ds.da_prices):.2f}",
                f"${np.nanmin(ds.da_prices):.2f}",
                f"${np.nanmax(ds.da_prices):.2f}",
                f"{int(np.sum(ds.da_prices > 200))}",
                f"{int(np.sum(ds.da_prices < 0))}",
            ],
        }
        if not np.allclose(ds.da_prices, ds.rt_prices):
            stats_data["RT Price"] = [
                f"${np.nanmean(ds.rt_prices):.2f}",
                f"${np.nanmedian(ds.rt_prices):.2f}",
                f"${np.nanstd(ds.rt_prices):.2f}",
                f"${np.nanmin(ds.rt_prices):.2f}",
                f"${np.nanmax(ds.rt_prices):.2f}",
                f"{int(np.sum(ds.rt_prices > 200))}",
                f"{int(np.sum(ds.rt_prices < 0))}",
            ]
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

    # Actual vs Theoretical (for SEN data)
    if ds.actual_mw is not None and ds.theoretical_mw is not None:
        st.markdown("#### Generation: Actual vs. Theoretical")
        fig_gen = go.Figure()
        x_axis = list(range(len(ds.actual_mw)))

        fig_gen.add_trace(go.Scatter(
            x=x_axis, y=ds.theoretical_mw,
            name="Theoretical (Optimal)", line=dict(color="#00ffcc", width=2),
        ))
        fig_gen.add_trace(go.Scatter(
            x=x_axis, y=ds.actual_mw,
            name="Actual", line=dict(color="#ff3333", width=1.5, dash="dash"),
        ))
        fig_gen.update_layout(
            template="plotly_dark",
            paper_bgcolor="#050810",
            plot_bgcolor="#0a0f1a",
            xaxis_title="Interval",
            yaxis_title="MW",
            height=350,
        )
        st.plotly_chart(fig_gen, use_container_width=True)

        # Savings preview
        gap_mwh = float(((ds.theoretical_mw - ds.actual_mw) * 0.25).sum())
        revenue_gap = float(((ds.theoretical_mw - ds.actual_mw) * ds.da_prices * 0.25).sum())
        st.markdown("#### 💰 Savings Preview")
        s1, s2 = st.columns(2)
        s1.metric("Energy Gap", f"{gap_mwh:,.1f} MWh",
                   help="Total energy difference between optimal and actual")
        s2.metric("Revenue Recovery Potential", f"${revenue_gap:,.2f}",
                   help="Additional revenue from optimal dispatch")

    # Column mapping details
    if ds.quality and ds.quality.columns_mapped:
        with st.expander("🔧 Column Mapping Details"):
            for internal, csv_col in ds.quality.columns_mapped.items():
                st.text(f"  {internal:20s} ← {csv_col}")

    # Warnings
    if ds.quality and ds.quality.warnings:
        with st.expander(f"⚠️ Warnings ({len(ds.quality.warnings)})"):
            for w in ds.quality.warnings:
                st.text(f"  {w}")

else:
    st.info(
        "👆 Upload a CSV file or load a default dataset to begin analysis.\n\n"
        "Once data is loaded, it will be available across all dashboard pages."
    )
