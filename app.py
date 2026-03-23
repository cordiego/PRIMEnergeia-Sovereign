import streamlit as st
st.set_page_config(page_title="PRIMEnergeia", page_icon="⚡", layout="wide")
st.markdown("# PRIMEnergeia Sovereign")
st.caption("UNIFIED COMMAND CENTER")
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("Grid Control")
    st.write("Multi-market HJB optimal frequency control. SEN, ERCOT, MIBEL.")
    st.page_link("pages/1_Grid_Control.py", label="Open Grid Control")
with c2:
    st.subheader("Eureka Sovereign")
    st.write("Dynamic VIX-Regime Volatility Targeting Engine.")
    st.page_link("pages/2_Eureka_Sovereign.py", label="Open Eureka")
with c3:
    st.subheader("Granas Optimizer")
    st.write("Sol-Ink Bayesian Optimizer for perovskite solar cells.")
    st.page_link("pages/3_Granas_Optimizer.py", label="Open Granas")
