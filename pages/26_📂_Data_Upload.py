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

# ─── Fetch Live Market Data (Multi-Market) ──────────────────
st.markdown("---")
st.markdown("### ⚡ Fetch Live Market Data")
st.markdown(
    "Download **real** settlement prices directly from public market sources. "
    "No API key required. Data is cached locally after first download."
)

market_tab_ercot, market_tab_sen, market_tab_mibel = st.tabs([
    "🇺🇸 ERCOT (Texas)", "🇲🇽 SEN (Mexico)", "🇪🇸🇵🇹 MIBEL (Iberia)"
])

# ── ERCOT Tab ──
with market_tab_ercot:
    ec1, ec2, ec3 = st.columns([2, 1, 1])
    with ec1:
        ercot_hub = st.selectbox(
            "Trading Hub",
            ["HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_BUSAVG"],
            format_func=lambda h: {
                "HB_HOUSTON": "🏙️ Houston Hub",
                "HB_NORTH": "📍 North Hub (DFW)",
                "HB_SOUTH": "📍 South Hub (SA/Austin)",
                "HB_WEST": "🏜️ West Hub (Permian)",
                "HB_BUSAVG": "📊 Bus Average (system-wide)",
            }.get(h, h),
            key="ercot_hub",
        )
    with ec2:
        ercot_days = st.selectbox("History", [7, 14, 30, 60, 90], index=2,
                                   format_func=lambda d: f"{d} days", key="ercot_days")
    with ec3:
        ercot_fetch = st.button("⚡ Fetch ERCOT", use_container_width=True, type="primary")

    if ercot_fetch:
        with st.spinner(f"Downloading {ercot_days} days of ERCOT {ercot_hub}..."):
            try:
                from fetch_ercot_real import fetch_ercot_data
                csv_path = fetch_ercot_data(days=ercot_days, hub=ercot_hub)
                is_proxy = "PROXY" in os.path.basename(csv_path).upper()
                source_label = (f"ERCOT PROXY {ercot_hub} ({ercot_days}d)" if is_proxy
                                else f"ERCOT Live {ercot_hub} ({ercot_days}d)")
                ds = load_dataset(filepath=csv_path, market="ercot")
                st.session_state["prime_dataset"] = ds
                st.session_state["prime_data_source"] = source_label
                if is_proxy:
                    st.warning(f"⚠ Proxy data loaded — {ds.hours} intervals. Install `gridstatus` for real prices.")
                else:
                    st.success(f"✅ **{ds.hours} ERCOT intervals loaded!** DA mean: ${float(np.nanmean(ds.da_prices)):.2f}/MWh")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fetch failed: {e}")

# ── SEN Tab ──
with market_tab_sen:
    sc1, sc2, sc3 = st.columns([2, 1, 1])
    with sc1:
        sen_nodes = [
            "05-VZA-400", "07-HER-230", "04-MTY-400", "03-GDL-400",
            "01-QRO-230", "02-OAX-230", "10-MER-230", "08-TIJ-230",
            "05-CHI-400", "06-SLP-400", "09-LAP-115", "08-MXL-230",
        ]
        sen_labels = {
            "05-VZA-400": "⭐ VZA-400 ($231K validated)",
            "07-HER-230": "🏜️ Hermosillo (Noroeste)",
            "04-MTY-400": "🏭 Monterrey (Noreste)",
            "03-GDL-400": "🌮 Guadalajara (Occidental)",
            "01-QRO-230": "🏛️ Querétaro (Central)",
            "02-OAX-230": "🌿 Oaxaca (Oriental)",
            "10-MER-230": "🏖️ Mérida (Peninsular)",
            "08-TIJ-230": "🌉 Tijuana (Baja California)",
            "05-CHI-400": "🏔️ Chihuahua (Norte)",
            "06-SLP-400": "⛰️ San Luis Potosí",
            "09-LAP-115": "🌊 La Paz (BCS)",
            "08-MXL-230": "🌵 Mexicali (BC)",
        }
        sen_node = st.selectbox("SEN Node", sen_nodes,
                                 format_func=lambda n: sen_labels.get(n, n),
                                 key="sen_node")
    with sc2:
        sen_days = st.selectbox("History", [7, 14, 30, 60], index=2,
                                 format_func=lambda d: f"{d} days", key="sen_days")
    with sc3:
        sen_fetch = st.button("⚡ Fetch SEN", use_container_width=True, type="primary")

    if sen_fetch:
        with st.spinner(f"Loading SEN {sen_node} data..."):
            try:
                from fetch_sen_real import fetch_sen_data
                csv_path = fetch_sen_data(node_id=sen_node, days=sen_days)
                is_proxy = "PROXY" in os.path.basename(csv_path).upper()
                source_label = (f"SEN PROXY {sen_node} ({sen_days}d)" if is_proxy
                                else f"SEN Live {sen_node}")
                ds = load_dataset(filepath=csv_path, market="sen")
                st.session_state["prime_dataset"] = ds
                st.session_state["prime_data_source"] = source_label
                if is_proxy:
                    st.warning(f"⚠ Proxy data — {ds.hours} intervals. Real nodo CSVs load automatically when available.")
                else:
                    st.success(f"✅ **{ds.hours} SEN intervals loaded!** PML mean: ${float(np.nanmean(ds.da_prices)):.2f}/MWh")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fetch failed: {e}")

# ── MIBEL Tab ──
with market_tab_mibel:
    mc1, mc2, mc3 = st.columns([2, 1, 1])
    with mc1:
        mibel_zones = ["ES", "PT", "ES_NORTE", "ES_SUR", "BALEARES"]
        mibel_labels = {
            "ES": "🇪🇸 España (Spain)",
            "PT": "🇵🇹 Portugal",
            "ES_NORTE": "📍 España Norte",
            "ES_SUR": "☀️ España Sur (Andalucía)",
            "BALEARES": "🏝️ Islas Baleares",
        }
        mibel_zone = st.selectbox("Zone", mibel_zones,
                                   format_func=lambda z: mibel_labels.get(z, z),
                                   key="mibel_zone")
    with mc2:
        mibel_days = st.selectbox("History", [7, 14, 30, 60, 90], index=2,
                                   format_func=lambda d: f"{d} days", key="mibel_days")
    with mc3:
        mibel_fetch = st.button("⚡ Fetch MIBEL", use_container_width=True, type="primary")

    if mibel_fetch:
        with st.spinner(f"Downloading {mibel_days} days of MIBEL {mibel_zone}..."):
            try:
                from fetch_mibel_real import fetch_mibel_data
                csv_path = fetch_mibel_data(days=mibel_days, zone=mibel_zone)
                is_proxy = "PROXY" in os.path.basename(csv_path).upper()
                source_label = (f"MIBEL PROXY {mibel_zone} ({mibel_days}d)" if is_proxy
                                else f"MIBEL Live {mibel_zone} ({mibel_days}d)")
                ds = load_dataset(filepath=csv_path, market="mibel")
                st.session_state["prime_dataset"] = ds
                st.session_state["prime_data_source"] = source_label
                if is_proxy:
                    st.warning(f"⚠ Proxy data — {ds.hours} intervals. Connect OMIE/ENTSO-E for real prices.")
                else:
                    st.success(f"✅ **{ds.hours} MIBEL intervals loaded!** DA mean: €{float(np.nanmean(ds.da_prices)):.2f}/MWh")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fetch failed: {e}")

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
