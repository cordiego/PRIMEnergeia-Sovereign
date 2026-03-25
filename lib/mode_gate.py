"""
PRIMEnergeia — Demo Banner & Mode Gate
=========================================
Injects a prominent DEMO/LIVE banner at the top of every Streamlit page
based on whether real data has been loaded.

Usage in a page:
    from lib.mode_gate import show_mode_banner, is_live_mode

    show_mode_banner()

    if not is_live_mode():
        st.info("Connect real data for live analysis.")

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import streamlit as st


def is_live_mode() -> bool:
    """Check if real data has been loaded into session state."""
    return "prime_dataset" in st.session_state


def show_mode_banner():
    """Show a prominent DEMO or LIVE banner at the top of the page."""
    if is_live_mode():
        ds = st.session_state["prime_dataset"]
        source = st.session_state.get("prime_data_source", "Unknown")
        is_proxy = "PROXY" in source.upper()

        if is_proxy:
            st.markdown("""
            <div style='background: linear-gradient(90deg, #ff8c00, #ff4500);
                        color: white; padding: 8px 16px; border-radius: 6px;
                        margin-bottom: 12px; font-weight: 600; font-size: 13px;'>
                ⚠ PROXY DATA MODE — Based on documented ERCOT patterns, not real settlement prices.
                Upload real data via 📂 Data Upload for production analysis.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='background: linear-gradient(90deg, #00cc88, #00aa66);
                        color: white; padding: 8px 16px; border-radius: 6px;
                        margin-bottom: 12px; font-weight: 600; font-size: 13px;'>
                ✅ LIVE DATA — {ds.market.upper()} | {ds.hours} intervals | Source: {source}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    color: white; padding: 10px 16px; border-radius: 6px;
                    margin-bottom: 12px; font-weight: 600; font-size: 13px;'>
            🔬 DEMONSTRATION MODE — Showing simulated data for product demonstration purposes.
            Navigate to 📂 Data Upload to connect real market data.
        </div>
        """, unsafe_allow_html=True)


def require_live_data(page_name: str = "this page"):
    """Gate a page behind live data. Show upload prompt if no data loaded."""
    show_mode_banner()
    if not is_live_mode():
        st.warning(f"**{page_name}** requires real market data to display live results.")
        st.page_link("pages/25_📂_Data_Upload.py", label="📂 Upload Data", icon="📂")
        return False
    return True
