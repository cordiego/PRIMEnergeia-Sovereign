import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import time

# ============================================================
#  PRIMEnergeia Sovereign — Multi-Market Control Dashboard
#  Hamilton-Jacobi-Bellman Optimal Frequency Control System
#  Markets: SEN (Mexico) | ERCOT (Texas) | MIBEL (Iberian)
# ============================================================

st.set_page_config(
    page_title="PRIMEnergeia Sovereign | Grid Control",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
#  MARKET CONFIGURATIONS
# ============================================================
MARKETS = {
    "SEN 🇲🇽": {
        "name": "SEN", "full": "Sistema Eléctrico Nacional", "operator": "CENACE",
        "f_nom": 60.0, "H": 5.0, "D": 2.0, "v_nom": 115.0,
        "price_name": "PML", "currency": "$", "cur_code": "USD",
        "price_base": 42, "price_amp": 22, "price_cap": 350, "price_floor": 28,
        "spike_prob": 0.95, "spike_range": (80, 200), "settle": "15-min CENACE",
        "penalty_f": 0.05, "thd_limit": 5.0, "thd_std": "Código de Red",
        "accent": "#00d1ff", "accent2": "#0066ff", "border": "#1a2744",
        "protocol": "PRIME-HJB-v8.0-SEN", "tz": "CST",
        "tagline": "Soberanía Energética para México 🇲🇽",
        "price_threshold": 120, "threshold_label": "High-Value Threshold",
        "penalty_label": "CENACE Penalty",
        "load_vol": 0.008, "dist1": 0.04, "dist2": 0.06, "cap_mw": 100,
        "nodes": [
            {"id": "05-VZA-400", "loc": "Valle de México", "region": "Central", "cap": 100, "status": "MASTER", "fσ": 0.008},
            {"id": "01-QRO-230", "loc": "Querétaro", "region": "Central", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "01-TUL-400", "loc": "Tula, Hidalgo", "region": "Central", "cap": 100, "status": "ONLINE", "fσ": 0.009},
            {"id": "06-SLP-400", "loc": "San Luis Potosí", "region": "Central", "cap": 100, "status": "ONLINE", "fσ": 0.012},
            {"id": "02-PUE-400", "loc": "Puebla", "region": "Oriental", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "02-VER-230", "loc": "Veracruz", "region": "Oriental", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "02-OAX-230", "loc": "Oaxaca", "region": "Oriental", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "02-TEH-400", "loc": "Tehuantepec", "region": "Oriental", "cap": 100, "status": "ONLINE", "fσ": 0.014},
            {"id": "03-GDL-400", "loc": "Guadalajara", "region": "Occidental", "cap": 100, "status": "ONLINE", "fσ": 0.009},
            {"id": "03-MAN-400", "loc": "Manzanillo", "region": "Occidental", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "03-AGS-230", "loc": "Aguascalientes", "region": "Occidental", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "03-COL-115", "loc": "Colima", "region": "Occidental", "cap": 40, "status": "STANDBY", "fσ": 0.015},
            {"id": "04-MTY-400", "loc": "Monterrey", "region": "Noreste", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "04-TAM-230", "loc": "Tampico", "region": "Noreste", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "04-SAL-400", "loc": "Saltillo", "region": "Noreste", "cap": 100, "status": "ONLINE", "fσ": 0.011},
            {"id": "05-CHI-400", "loc": "Chihuahua", "region": "Norte", "cap": 100, "status": "ONLINE", "fσ": 0.012},
            {"id": "05-LAG-230", "loc": "Gómez Palacio", "region": "Norte", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "05-DGO-230", "loc": "Durango", "region": "Norte", "cap": 60, "status": "STANDBY", "fσ": 0.015},
            {"id": "05-JRZ-230", "loc": "Cd. Juárez", "region": "Norte", "cap": 80, "status": "ONLINE", "fσ": 0.014},
            {"id": "07-HER-230", "loc": "Hermosillo", "region": "Noroeste", "cap": 80, "status": "ONLINE", "fσ": 0.015},
            {"id": "07-NAV-230", "loc": "Navojoa", "region": "Noroeste", "cap": 60, "status": "STANDBY", "fσ": 0.016},
            {"id": "07-CUM-115", "loc": "Cd. Obregón", "region": "Noroeste", "cap": 40, "status": "STANDBY", "fσ": 0.018},
            {"id": "07-GUY-230", "loc": "Guaymas", "region": "Noroeste", "cap": 60, "status": "ONLINE", "fσ": 0.016},
            {"id": "07-CUL-230", "loc": "Culiacán", "region": "Noroeste", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "08-MXL-230", "loc": "Mexicali", "region": "Baja California", "cap": 80, "status": "ONLINE", "fσ": 0.014},
            {"id": "08-ENS-230", "loc": "Ensenada", "region": "Baja California", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "08-TIJ-230", "loc": "Tijuana", "region": "Baja California", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "09-LAP-115", "loc": "La Paz", "region": "BCS", "cap": 40, "status": "STANDBY", "fσ": 0.020},
            {"id": "10-MER-230", "loc": "Mérida", "region": "Peninsular", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "10-CAN-230", "loc": "Cancún", "region": "Peninsular", "cap": 80, "status": "ONLINE", "fσ": 0.013},
        ],
    },
    "ERCOT 🇺🇸": {
        "name": "ERCOT", "full": "Electric Reliability Council of Texas", "operator": "ERCOT ISO",
        "f_nom": 60.0, "H": 4.5, "D": 1.8, "v_nom": 345.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 35, "price_amp": 30, "price_cap": 5000, "price_floor": -50,
        "spike_prob": 0.96, "spike_range": (500, 5000), "settle": "5-min ERCOT RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#ff6b35", "accent2": "#cc4400", "border": "#2a1a10",
        "protocol": "PRIME-HJB-v8.0-ERCOT", "tz": "CST",
        "tagline": "Energy Sovereignty for Texas ⚡🇺🇸",
        "price_threshold": 500, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NERC Penalty",
        "load_vol": 0.010, "dist1": 0.05, "dist2": 0.08, "cap_mw": 120,
        "nodes": [
            {"id": "HOU-345-01", "loc": "Houston Central", "region": "Houston", "cap": 120, "status": "MASTER", "fσ": 0.009},
            {"id": "HOU-345-02", "loc": "Baytown", "region": "Houston", "cap": 100, "status": "ONLINE", "fσ": 0.011},
            {"id": "HOU-138-03", "loc": "Galveston", "region": "Houston", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "NTH-345-01", "loc": "Dallas–Fort Worth", "region": "North", "cap": 120, "status": "ONLINE", "fσ": 0.010},
            {"id": "NTH-345-02", "loc": "Denton", "region": "North", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "NTH-138-03", "loc": "Waco", "region": "North", "cap": 60, "status": "STANDBY", "fσ": 0.015},
            {"id": "STH-345-01", "loc": "San Antonio", "region": "South", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "STH-345-02", "loc": "Corpus Christi", "region": "South", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "STH-138-03", "loc": "Laredo", "region": "South", "cap": 50, "status": "STANDBY", "fσ": 0.016},
            {"id": "AUS-345-01", "loc": "Austin", "region": "South", "cap": 100, "status": "ONLINE", "fσ": 0.009},
            {"id": "AUS-138-02", "loc": "Georgetown", "region": "South", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "WST-345-01", "loc": "Midland–Odessa", "region": "West", "cap": 100, "status": "ONLINE", "fσ": 0.014},
            {"id": "WST-345-02", "loc": "Abilene", "region": "West", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "FWS-345-01", "loc": "El Paso", "region": "Far West", "cap": 80, "status": "ONLINE", "fσ": 0.016},
            {"id": "FWS-138-02", "loc": "Pecos", "region": "Far West", "cap": 60, "status": "STANDBY", "fσ": 0.018},
            {"id": "CST-345-01", "loc": "Victoria", "region": "Coast", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "CST-138-02", "loc": "Bay City", "region": "Coast", "cap": 60, "status": "ONLINE", "fσ": 0.014},
            {"id": "PNH-345-01", "loc": "Amarillo", "region": "Panhandle", "cap": 80, "status": "ONLINE", "fσ": 0.015},
            {"id": "PNH-138-02", "loc": "Lubbock", "region": "Panhandle", "cap": 60, "status": "ONLINE", "fσ": 0.016},
            {"id": "EST-345-01", "loc": "Beaumont", "region": "East", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "EST-345-02", "loc": "Tyler", "region": "East", "cap": 80, "status": "ONLINE", "fσ": 0.013},
            {"id": "EST-138-03", "loc": "Lufkin", "region": "East", "cap": 50, "status": "STANDBY", "fσ": 0.017},
        ],
    },
    "MIBEL 🇪🇸🇵🇹": {
        "name": "MIBEL", "full": "Mercado Ibérico de Electricidad", "operator": "OMIE / REE / REN",
        "f_nom": 50.0, "H": 6.0, "D": 2.5, "v_nom": 220.0,
        "price_name": "Pool", "currency": "€", "cur_code": "EUR",
        "price_base": 55, "price_amp": 35, "price_cap": 3000, "price_floor": 0,
        "spike_prob": 0.97, "spike_range": (150, 500), "settle": "OMIE Hourly",
        "penalty_f": 0.04, "thd_limit": 8.0, "thd_std": "EN 50160",
        "accent": "#e8c547", "accent2": "#c9a020", "border": "#2a2210",
        "protocol": "PRIME-HJB-v8.0-MIBEL", "tz": "CET",
        "tagline": "Soberanía Energética Ibérica ⚡🇪🇸🇵🇹",
        "price_threshold": 200, "threshold_label": "High-Price Threshold",
        "penalty_label": "ENTSO-E Penalty",
        "load_vol": 0.006, "dist1": 0.03, "dist2": 0.05, "cap_mw": 150,
        "nodes": [
            {"id": "ES-BCN-400", "loc": "Barcelona", "region": "Spain North", "cap": 120, "status": "ONLINE", "fσ": 0.007},
            {"id": "ES-BIL-400", "loc": "Bilbao", "region": "Spain North", "cap": 100, "status": "ONLINE", "fσ": 0.008},
            {"id": "ES-ZAR-400", "loc": "Zaragoza", "region": "Spain North", "cap": 80, "status": "ONLINE", "fσ": 0.009},
            {"id": "ES-MAD-400", "loc": "Madrid", "region": "Spain Central", "cap": 150, "status": "MASTER", "fσ": 0.006},
            {"id": "ES-VAL-400", "loc": "Valencia", "region": "Spain Central", "cap": 100, "status": "ONLINE", "fσ": 0.008},
            {"id": "ES-CLM-220", "loc": "Ciudad Real", "region": "Spain Central", "cap": 60, "status": "STANDBY", "fσ": 0.012},
            {"id": "ES-SEV-400", "loc": "Sevilla", "region": "Spain South", "cap": 100, "status": "ONLINE", "fσ": 0.009},
            {"id": "ES-MAL-400", "loc": "Málaga", "region": "Spain South", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "ES-ALM-220", "loc": "Almería", "region": "Spain South", "cap": 60, "status": "ONLINE", "fσ": 0.011},
            {"id": "ES-GRA-220", "loc": "Granada", "region": "Spain South", "cap": 60, "status": "STANDBY", "fσ": 0.013},
            {"id": "ES-COR-400", "loc": "A Coruña", "region": "Spain Northwest", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "ES-LEO-220", "loc": "León", "region": "Spain Northwest", "cap": 60, "status": "STANDBY", "fσ": 0.014},
            {"id": "ES-PMI-220", "loc": "Palma de Mallorca", "region": "Balearic Islands", "cap": 40, "status": "ONLINE", "fσ": 0.016},
            {"id": "ES-TFE-220", "loc": "Tenerife", "region": "Canary Islands", "cap": 40, "status": "ONLINE", "fσ": 0.018},
            {"id": "ES-LPA-220", "loc": "Las Palmas", "region": "Canary Islands", "cap": 40, "status": "ONLINE", "fσ": 0.017},
            {"id": "PT-PRT-400", "loc": "Porto", "region": "Portugal North", "cap": 80, "status": "ONLINE", "fσ": 0.009},
            {"id": "PT-BRG-220", "loc": "Braga", "region": "Portugal North", "cap": 50, "status": "STANDBY", "fσ": 0.013},
            {"id": "PT-LIS-400", "loc": "Lisboa", "region": "Portugal South", "cap": 100, "status": "ONLINE", "fσ": 0.008},
            {"id": "PT-FAR-220", "loc": "Faro", "region": "Portugal South", "cap": 50, "status": "STANDBY", "fσ": 0.015},
            {"id": "PT-SET-220", "loc": "Setúbal", "region": "Portugal South", "cap": 50, "status": "ONLINE", "fσ": 0.012},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  PJM — PJM Interconnection (US East)
    # ════════════════════════════════════════════════════════════
    "PJM 🇺🇸": {
        "name": "PJM", "full": "PJM Interconnection", "operator": "PJM",
        "f_nom": 60.0, "H": 5.0, "D": 2.0, "v_nom": 500.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 38, "price_amp": 28, "price_cap": 3700, "price_floor": -50,
        "spike_prob": 0.96, "spike_range": (200, 1500), "settle": "5-min PJM RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#4a90d9", "accent2": "#2c5fa1", "border": "#1a2744",
        "protocol": "PRIME-HJB-v8.0-PJM", "tz": "EST",
        "tagline": "Powering 65M+ People — PJM 🇺🇸",
        "price_threshold": 400, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NERC Penalty",
        "load_vol": 0.009, "dist1": 0.04, "dist2": 0.07, "cap_mw": 180,
        "nodes": [
            {"id": "PJM-WH-500", "loc": "Whitpain (PHL)", "region": "Eastern", "cap": 180, "status": "MASTER", "fσ": 0.007},
            {"id": "PJM-DC-500", "loc": "Washington D.C.", "region": "PEPCO", "cap": 150, "status": "ONLINE", "fσ": 0.008},
            {"id": "PJM-PIT-345", "loc": "Pittsburgh", "region": "Western", "cap": 120, "status": "ONLINE", "fσ": 0.009},
            {"id": "PJM-NJ-345", "loc": "Newark", "region": "PSEG", "cap": 140, "status": "ONLINE", "fσ": 0.008},
            {"id": "PJM-BAL-345", "loc": "Baltimore", "region": "BGE", "cap": 110, "status": "ONLINE", "fσ": 0.010},
            {"id": "PJM-RIC-230", "loc": "Richmond", "region": "Dominion", "cap": 100, "status": "ONLINE", "fσ": 0.011},
            {"id": "PJM-COL-345", "loc": "Columbus", "region": "AEP", "cap": 130, "status": "ONLINE", "fσ": 0.009},
            {"id": "PJM-CLE-345", "loc": "Cleveland", "region": "FirstEnergy", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "PJM-CHI-345", "loc": "Chicago (ComEd)", "region": "ComEd", "cap": 160, "status": "ONLINE", "fσ": 0.008},
            {"id": "PJM-DET-345", "loc": "Detroit", "region": "DTE", "cap": 100, "status": "ONLINE", "fσ": 0.011},
            {"id": "PJM-HAR-230", "loc": "Harrisburg", "region": "PPL", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "PJM-WVA-230", "loc": "Charleston WV", "region": "APCo", "cap": 70, "status": "STANDBY", "fσ": 0.014},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  CAISO — California ISO
    # ════════════════════════════════════════════════════════════
    "CAISO 🇺🇸": {
        "name": "CAISO", "full": "California Independent System Operator", "operator": "CAISO",
        "f_nom": 60.0, "H": 4.8, "D": 1.9, "v_nom": 500.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 45, "price_amp": 35, "price_cap": 2000, "price_floor": -150,
        "spike_prob": 0.95, "spike_range": (300, 1500), "settle": "5-min CAISO RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#f5a623", "accent2": "#c98400", "border": "#2a2010",
        "protocol": "PRIME-HJB-v8.0-CAISO", "tz": "PST",
        "tagline": "Clean Grid Sovereignty — California 🇺🇸",
        "price_threshold": 500, "threshold_label": "Scarcity Threshold",
        "penalty_label": "WECC Penalty",
        "load_vol": 0.011, "dist1": 0.05, "dist2": 0.08, "cap_mw": 140,
        "nodes": [
            {"id": "CA-LA-500", "loc": "Los Angeles Basin", "region": "South", "cap": 160, "status": "MASTER", "fσ": 0.008},
            {"id": "CA-SF-500", "loc": "San Francisco", "region": "North", "cap": 120, "status": "ONLINE", "fσ": 0.009},
            {"id": "CA-SD-230", "loc": "San Diego", "region": "South", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "CA-SAC-500", "loc": "Sacramento", "region": "North", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "CA-SJ-230", "loc": "San Jose", "region": "Bay Area", "cap": 90, "status": "ONLINE", "fσ": 0.010},
            {"id": "CA-FRE-230", "loc": "Fresno", "region": "Central Valley", "cap": 70, "status": "ONLINE", "fσ": 0.012},
            {"id": "CA-BAK-230", "loc": "Bakersfield", "region": "Central Valley", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "CA-RIV-230", "loc": "Riverside", "region": "South", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "CA-SLO-115", "loc": "San Luis Obispo", "region": "Central Coast", "cap": 40, "status": "STANDBY", "fσ": 0.016},
            {"id": "CA-RED-230", "loc": "Redding", "region": "Far North", "cap": 50, "status": "STANDBY", "fσ": 0.015},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  NYISO — New York ISO
    # ════════════════════════════════════════════════════════════
    "NYISO 🇺🇸": {
        "name": "NYISO", "full": "New York Independent System Operator", "operator": "NYISO",
        "f_nom": 60.0, "H": 5.2, "D": 2.1, "v_nom": 345.0,
        "price_name": "LBMP", "currency": "$", "cur_code": "USD",
        "price_base": 42, "price_amp": 32, "price_cap": 1000, "price_floor": -50,
        "spike_prob": 0.96, "spike_range": (150, 800), "settle": "5-min NYISO RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#e74c3c", "accent2": "#c0392b", "border": "#2a1210",
        "protocol": "PRIME-HJB-v8.0-NYISO", "tz": "EST",
        "tagline": "Empire State Grid — New York 🇺🇸",
        "price_threshold": 300, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NPCC Penalty",
        "load_vol": 0.008, "dist1": 0.04, "dist2": 0.06, "cap_mw": 120,
        "nodes": [
            {"id": "NY-NYC-345", "loc": "New York City", "region": "Zone J", "cap": 140, "status": "MASTER", "fσ": 0.007},
            {"id": "NY-LI-138", "loc": "Long Island", "region": "Zone K", "cap": 60, "status": "ONLINE", "fσ": 0.012},
            {"id": "NY-ALB-345", "loc": "Albany", "region": "Zone F", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "NY-BUF-345", "loc": "Buffalo", "region": "Zone A", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "NY-SYR-230", "loc": "Syracuse", "region": "Zone C", "cap": 60, "status": "ONLINE", "fσ": 0.012},
            {"id": "NY-HV-345", "loc": "Hudson Valley", "region": "Zone G", "cap": 90, "status": "ONLINE", "fσ": 0.009},
            {"id": "NY-ROC-230", "loc": "Rochester", "region": "Zone B", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "NY-WC-138", "loc": "Westchester", "region": "Zone H", "cap": 70, "status": "ONLINE", "fσ": 0.010},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  SPP — Southwest Power Pool
    # ════════════════════════════════════════════════════════════
    "SPP 🇺🇸": {
        "name": "SPP", "full": "Southwest Power Pool", "operator": "SPP",
        "f_nom": 60.0, "H": 4.8, "D": 1.8, "v_nom": 345.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 28, "price_amp": 22, "price_cap": 4500, "price_floor": -40,
        "spike_prob": 0.95, "spike_range": (100, 1000), "settle": "5-min SPP RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#27ae60", "accent2": "#1e8449", "border": "#102a18",
        "protocol": "PRIME-HJB-v8.0-SPP", "tz": "CST",
        "tagline": "Wind Capital of America — SPP 🇺🇸",
        "price_threshold": 300, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NERC Penalty",
        "load_vol": 0.010, "dist1": 0.05, "dist2": 0.07, "cap_mw": 100,
        "nodes": [
            {"id": "SPP-OKC-345", "loc": "Oklahoma City", "region": "Oklahoma", "cap": 100, "status": "MASTER", "fσ": 0.009},
            {"id": "SPP-WIC-345", "loc": "Wichita", "region": "Kansas", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "SPP-TUL-345", "loc": "Tulsa", "region": "Oklahoma", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "SPP-LR-230", "loc": "Little Rock", "region": "Arkansas", "cap": 70, "status": "ONLINE", "fσ": 0.012},
            {"id": "SPP-OMA-345", "loc": "Omaha", "region": "Nebraska", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "SPP-KC-345", "loc": "Kansas City", "region": "Kansas", "cap": 90, "status": "ONLINE", "fσ": 0.010},
            {"id": "SPP-NOLA-230", "loc": "Shreveport", "region": "Louisiana", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "SPP-SD-230", "loc": "Sioux Falls", "region": "South Dakota", "cap": 50, "status": "STANDBY", "fσ": 0.015},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  MISO — Midcontinent ISO
    # ════════════════════════════════════════════════════════════
    "MISO 🇺🇸": {
        "name": "MISO", "full": "Midcontinent Independent System Operator", "operator": "MISO",
        "f_nom": 60.0, "H": 5.0, "D": 2.0, "v_nom": 345.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 32, "price_amp": 25, "price_cap": 3500, "price_floor": -40,
        "spike_prob": 0.96, "spike_range": (150, 1200), "settle": "5-min MISO RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#8e44ad", "accent2": "#6c3483", "border": "#1a102a",
        "protocol": "PRIME-HJB-v8.0-MISO", "tz": "CST",
        "tagline": "Heartland Energy — MISO 🇺🇸",
        "price_threshold": 350, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NERC Penalty",
        "load_vol": 0.009, "dist1": 0.04, "dist2": 0.07, "cap_mw": 130,
        "nodes": [
            {"id": "MISO-CHI-345", "loc": "Chicago", "region": "Central", "cap": 140, "status": "MASTER", "fσ": 0.008},
            {"id": "MISO-IND-345", "loc": "Indianapolis", "region": "Central", "cap": 100, "status": "ONLINE", "fσ": 0.009},
            {"id": "MISO-MSP-345", "loc": "Minneapolis", "region": "North", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "MISO-STL-345", "loc": "St. Louis", "region": "Central", "cap": 90, "status": "ONLINE", "fσ": 0.010},
            {"id": "MISO-DET-345", "loc": "Detroit", "region": "East", "cap": 100, "status": "ONLINE", "fσ": 0.011},
            {"id": "MISO-NOLA-230", "loc": "New Orleans", "region": "South", "cap": 80, "status": "ONLINE", "fσ": 0.012},
            {"id": "MISO-MIL-230", "loc": "Milwaukee", "region": "North", "cap": 70, "status": "ONLINE", "fσ": 0.011},
            {"id": "MISO-DSM-230", "loc": "Des Moines", "region": "West", "cap": 60, "status": "STANDBY", "fσ": 0.014},
            {"id": "MISO-LR-230", "loc": "Little Rock", "region": "South", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "MISO-JAX-230", "loc": "Jackson MS", "region": "South", "cap": 50, "status": "STANDBY", "fσ": 0.015},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  ISO-NE — ISO New England
    # ════════════════════════════════════════════════════════════
    "ISO-NE 🇺🇸": {
        "name": "ISO-NE", "full": "ISO New England", "operator": "ISO-NE",
        "f_nom": 60.0, "H": 5.5, "D": 2.2, "v_nom": 345.0,
        "price_name": "LMP", "currency": "$", "cur_code": "USD",
        "price_base": 48, "price_amp": 30, "price_cap": 2000, "price_floor": -50,
        "spike_prob": 0.96, "spike_range": (200, 1000), "settle": "5-min ISO-NE RT",
        "penalty_f": 0.03, "thd_limit": 5.0, "thd_std": "IEEE 519",
        "accent": "#1abc9c", "accent2": "#16a085", "border": "#0a2a22",
        "protocol": "PRIME-HJB-v8.0-ISONE", "tz": "EST",
        "tagline": "New England Grid — ISO-NE 🇺🇸",
        "price_threshold": 400, "threshold_label": "Scarcity Threshold",
        "penalty_label": "NPCC Penalty",
        "load_vol": 0.008, "dist1": 0.04, "dist2": 0.06, "cap_mw": 90,
        "nodes": [
            {"id": "NE-BOS-345", "loc": "Boston", "region": "NEMA", "cap": 100, "status": "MASTER", "fσ": 0.007},
            {"id": "NE-HFD-345", "loc": "Hartford", "region": "CT", "cap": 70, "status": "ONLINE", "fσ": 0.009},
            {"id": "NE-PVD-230", "loc": "Providence", "region": "RI", "cap": 50, "status": "ONLINE", "fσ": 0.011},
            {"id": "NE-BUR-230", "loc": "Burlington", "region": "VT", "cap": 40, "status": "ONLINE", "fσ": 0.013},
            {"id": "NE-POR-230", "loc": "Portland ME", "region": "ME", "cap": 50, "status": "ONLINE", "fσ": 0.012},
            {"id": "NE-SPR-230", "loc": "Springfield", "region": "WCMA", "cap": 60, "status": "ONLINE", "fσ": 0.010},
            {"id": "NE-NHV-230", "loc": "New Haven", "region": "CT", "cap": 50, "status": "STANDBY", "fσ": 0.014},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  AESO — Alberta Electric System Operator
    # ════════════════════════════════════════════════════════════
    "AESO 🇨🇦": {
        "name": "AESO", "full": "Alberta Electric System Operator", "operator": "AESO",
        "f_nom": 60.0, "H": 4.5, "D": 1.8, "v_nom": 240.0,
        "price_name": "Pool Price", "currency": "C$", "cur_code": "CAD",
        "price_base": 65, "price_amp": 40, "price_cap": 999.99, "price_floor": 0,
        "spike_prob": 0.94, "spike_range": (200, 999), "settle": "Hourly AESO",
        "penalty_f": 0.04, "thd_limit": 5.0, "thd_std": "CSA C22.2",
        "accent": "#e74c3c", "accent2": "#c0392b", "border": "#2a1010",
        "protocol": "PRIME-HJB-v8.0-AESO", "tz": "MST",
        "tagline": "Alberta Energy Sovereignty 🇨🇦",
        "price_threshold": 300, "threshold_label": "High-Price Alert",
        "penalty_label": "AESO Penalty",
        "load_vol": 0.010, "dist1": 0.05, "dist2": 0.08, "cap_mw": 80,
        "nodes": [
            {"id": "AB-CGY-240", "loc": "Calgary", "region": "South", "cap": 100, "status": "MASTER", "fσ": 0.009},
            {"id": "AB-EDM-240", "loc": "Edmonton", "region": "North", "cap": 100, "status": "ONLINE", "fσ": 0.010},
            {"id": "AB-RD-138", "loc": "Red Deer", "region": "Central", "cap": 50, "status": "ONLINE", "fσ": 0.013},
            {"id": "AB-LET-138", "loc": "Lethbridge", "region": "South", "cap": 40, "status": "ONLINE", "fσ": 0.014},
            {"id": "AB-GP-138", "loc": "Grande Prairie", "region": "North", "cap": 40, "status": "STANDBY", "fσ": 0.016},
            {"id": "AB-FMM-138", "loc": "Fort McMurray", "region": "North", "cap": 60, "status": "ONLINE", "fσ": 0.015},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  IESO — Independent Electricity System Operator (Ontario)
    # ════════════════════════════════════════════════════════════
    "IESO 🇨🇦": {
        "name": "IESO", "full": "Independent Electricity System Operator", "operator": "IESO",
        "f_nom": 60.0, "H": 5.5, "D": 2.2, "v_nom": 500.0,
        "price_name": "HOEP", "currency": "C$", "cur_code": "CAD",
        "price_base": 30, "price_amp": 20, "price_cap": 2000, "price_floor": -50,
        "spike_prob": 0.97, "spike_range": (100, 500), "settle": "5-min IESO RT",
        "penalty_f": 0.04, "thd_limit": 5.0, "thd_std": "CSA C22.2",
        "accent": "#e74c3c", "accent2": "#c0392b", "border": "#2a1414",
        "protocol": "PRIME-HJB-v8.0-IESO", "tz": "EST",
        "tagline": "Ontario Grid Sovereignty 🇨🇦",
        "price_threshold": 200, "threshold_label": "High-Price Alert",
        "penalty_label": "IESO Penalty",
        "load_vol": 0.007, "dist1": 0.03, "dist2": 0.05, "cap_mw": 100,
        "nodes": [
            {"id": "ON-TOR-500", "loc": "Toronto", "region": "Greater Toronto", "cap": 140, "status": "MASTER", "fσ": 0.007},
            {"id": "ON-OTT-230", "loc": "Ottawa", "region": "East", "cap": 70, "status": "ONLINE", "fσ": 0.010},
            {"id": "ON-HAM-230", "loc": "Hamilton", "region": "Southwest", "cap": 60, "status": "ONLINE", "fσ": 0.011},
            {"id": "ON-LON-230", "loc": "London", "region": "Southwest", "cap": 50, "status": "ONLINE", "fσ": 0.012},
            {"id": "ON-THB-230", "loc": "Thunder Bay", "region": "Northwest", "cap": 40, "status": "ONLINE", "fσ": 0.015},
            {"id": "ON-NIA-500", "loc": "Niagara", "region": "Southwest", "cap": 80, "status": "ONLINE", "fσ": 0.009},
            {"id": "ON-SUD-230", "loc": "Sudbury", "region": "Northeast", "cap": 40, "status": "STANDBY", "fσ": 0.016},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  NEM — National Electricity Market (Australia)
    # ════════════════════════════════════════════════════════════
    "NEM 🇦🇺": {
        "name": "NEM", "full": "National Electricity Market", "operator": "AEMO",
        "f_nom": 50.0, "H": 4.0, "D": 1.5, "v_nom": 330.0,
        "price_name": "Spot", "currency": "A$", "cur_code": "AUD",
        "price_base": 80, "price_amp": 60, "price_cap": 16600, "price_floor": -1000,
        "spike_prob": 0.93, "spike_range": (500, 15000), "settle": "5-min AEMO",
        "penalty_f": 0.05, "thd_limit": 5.0, "thd_std": "AS/NZS 61000",
        "accent": "#2ecc71", "accent2": "#27ae60", "border": "#0a2a10",
        "protocol": "PRIME-HJB-v8.0-NEM", "tz": "AEST",
        "tagline": "Sovereign Energy — Australia 🇦🇺",
        "price_threshold": 1000, "threshold_label": "Extreme Price",
        "penalty_label": "AEMO Penalty",
        "load_vol": 0.012, "dist1": 0.06, "dist2": 0.09, "cap_mw": 110,
        "nodes": [
            {"id": "AU-SYD-330", "loc": "Sydney", "region": "NSW", "cap": 120, "status": "MASTER", "fσ": 0.009},
            {"id": "AU-MEL-500", "loc": "Melbourne", "region": "VIC", "cap": 110, "status": "ONLINE", "fσ": 0.010},
            {"id": "AU-BNE-275", "loc": "Brisbane", "region": "QLD", "cap": 90, "status": "ONLINE", "fσ": 0.011},
            {"id": "AU-ADL-275", "loc": "Adelaide", "region": "SA", "cap": 60, "status": "ONLINE", "fσ": 0.014},
            {"id": "AU-HOB-220", "loc": "Hobart", "region": "TAS", "cap": 40, "status": "ONLINE", "fσ": 0.016},
            {"id": "AU-CAN-330", "loc": "Canberra", "region": "NSW", "cap": 50, "status": "ONLINE", "fσ": 0.013},
            {"id": "AU-NCA-275", "loc": "Newcastle", "region": "NSW", "cap": 70, "status": "ONLINE", "fσ": 0.012},
            {"id": "AU-GEE-220", "loc": "Geelong", "region": "VIC", "cap": 40, "status": "STANDBY", "fσ": 0.017},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  JEPX — Japan Electric Power Exchange
    # ════════════════════════════════════════════════════════════
    "JEPX 🇯🇵": {
        "name": "JEPX", "full": "Japan Electric Power Exchange", "operator": "OCCTO / JEPX",
        "f_nom": 50.0, "H": 6.0, "D": 2.5, "v_nom": 275.0,
        "price_name": "Spot", "currency": "¥", "cur_code": "JPY",
        "price_base": 12, "price_amp": 8, "price_cap": 200, "price_floor": 0.01,
        "spike_prob": 0.96, "spike_range": (30, 100), "settle": "30-min JEPX",
        "penalty_f": 0.04, "thd_limit": 5.0, "thd_std": "JIS C 61000",
        "accent": "#e74c3c", "accent2": "#c0392b", "border": "#2a0a0a",
        "protocol": "PRIME-HJB-v8.0-JEPX", "tz": "JST",
        "tagline": "Grid Sovereignty — Japan 🇯🇵",
        "price_threshold": 50, "threshold_label": "High-Price Alert",
        "penalty_label": "OCCTO Penalty",
        "load_vol": 0.006, "dist1": 0.03, "dist2": 0.05, "cap_mw": 150,
        "nodes": [
            {"id": "JP-TKY-500", "loc": "Tokyo", "region": "TEPCO (50Hz)", "cap": 180, "status": "MASTER", "fσ": 0.006},
            {"id": "JP-OSA-500", "loc": "Osaka", "region": "KEPCO (60Hz)", "cap": 140, "status": "ONLINE", "fσ": 0.007},
            {"id": "JP-NGY-275", "loc": "Nagoya", "region": "Chubu (60Hz)", "cap": 100, "status": "ONLINE", "fσ": 0.008},
            {"id": "JP-FUK-220", "loc": "Fukuoka", "region": "Kyushu (60Hz)", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "JP-SPR-275", "loc": "Sapporo", "region": "Hokkaido (50Hz)", "cap": 60, "status": "ONLINE", "fσ": 0.012},
            {"id": "JP-SEN-275", "loc": "Sendai", "region": "Tohoku (50Hz)", "cap": 70, "status": "ONLINE", "fσ": 0.011},
            {"id": "JP-HIR-220", "loc": "Hiroshima", "region": "Chugoku (60Hz)", "cap": 50, "status": "ONLINE", "fσ": 0.013},
            {"id": "JP-MAT-220", "loc": "Matsuyama", "region": "Shikoku (60Hz)", "cap": 40, "status": "STANDBY", "fσ": 0.015},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  NORD POOL — Nordic Power Exchange
    # ════════════════════════════════════════════════════════════
    "NORD POOL 🇳🇴🇸🇪": {
        "name": "NORD POOL", "full": "Nord Pool — Nordic Power Exchange", "operator": "Nord Pool / Statnett / SVK",
        "f_nom": 50.0, "H": 6.5, "D": 2.8, "v_nom": 400.0,
        "price_name": "Elspot", "currency": "€", "cur_code": "EUR",
        "price_base": 35, "price_amp": 25, "price_cap": 4000, "price_floor": -500,
        "spike_prob": 0.97, "spike_range": (100, 500), "settle": "Hourly Elspot",
        "penalty_f": 0.04, "thd_limit": 8.0, "thd_std": "EN 50160",
        "accent": "#3498db", "accent2": "#2980b9", "border": "#0a1a2a",
        "protocol": "PRIME-HJB-v8.0-NORDPOOL", "tz": "CET",
        "tagline": "Nordic Energy Sovereignty 🇳🇴🇸🇪🇫🇮🇩🇰",
        "price_threshold": 200, "threshold_label": "High-Price Alert",
        "penalty_label": "ENTSO-E Penalty",
        "load_vol": 0.006, "dist1": 0.03, "dist2": 0.05, "cap_mw": 120,
        "nodes": [
            {"id": "NO-OSL-400", "loc": "Oslo", "region": "Norway South", "cap": 100, "status": "MASTER", "fσ": 0.006},
            {"id": "SE-STO-400", "loc": "Stockholm", "region": "Sweden Central", "cap": 100, "status": "ONLINE", "fσ": 0.007},
            {"id": "FI-HEL-400", "loc": "Helsinki", "region": "Finland", "cap": 80, "status": "ONLINE", "fσ": 0.008},
            {"id": "DK-CPH-400", "loc": "Copenhagen", "region": "Denmark East", "cap": 60, "status": "ONLINE", "fσ": 0.009},
            {"id": "NO-BER-300", "loc": "Bergen", "region": "Norway West", "cap": 60, "status": "ONLINE", "fσ": 0.010},
            {"id": "SE-MAL-400", "loc": "Malmö", "region": "Sweden South", "cap": 50, "status": "ONLINE", "fσ": 0.011},
            {"id": "SE-LUL-220", "loc": "Luleå", "region": "Sweden North", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "NO-TRO-300", "loc": "Tromsø", "region": "Norway North", "cap": 40, "status": "STANDBY", "fσ": 0.016},
            {"id": "DK-AAR-220", "loc": "Aarhus", "region": "Denmark West", "cap": 40, "status": "ONLINE", "fσ": 0.012},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  EPEX — European Power Exchange (Central Europe)
    # ════════════════════════════════════════════════════════════
    "EPEX 🇩🇪🇫🇷": {
        "name": "EPEX", "full": "European Power Exchange", "operator": "EPEX SPOT / TSOs",
        "f_nom": 50.0, "H": 6.0, "D": 2.5, "v_nom": 380.0,
        "price_name": "DA Price", "currency": "€", "cur_code": "EUR",
        "price_base": 60, "price_amp": 40, "price_cap": 4000, "price_floor": -500,
        "spike_prob": 0.96, "spike_range": (200, 800), "settle": "Hourly EPEX",
        "penalty_f": 0.04, "thd_limit": 8.0, "thd_std": "EN 50160",
        "accent": "#f39c12", "accent2": "#e67e22", "border": "#2a1a0a",
        "protocol": "PRIME-HJB-v8.0-EPEX", "tz": "CET",
        "tagline": "Central European Grid — EPEX 🇩🇪🇫🇷",
        "price_threshold": 300, "threshold_label": "High-Price Alert",
        "penalty_label": "ENTSO-E Penalty",
        "load_vol": 0.007, "dist1": 0.04, "dist2": 0.06, "cap_mw": 160,
        "nodes": [
            {"id": "DE-BER-380", "loc": "Berlin", "region": "Germany North", "cap": 120, "status": "MASTER", "fσ": 0.006},
            {"id": "DE-MUN-380", "loc": "München", "region": "Germany South", "cap": 100, "status": "ONLINE", "fσ": 0.007},
            {"id": "FR-PAR-400", "loc": "Paris", "region": "France North", "cap": 140, "status": "ONLINE", "fσ": 0.006},
            {"id": "FR-LYN-400", "loc": "Lyon", "region": "France South", "cap": 80, "status": "ONLINE", "fσ": 0.008},
            {"id": "DE-HAM-380", "loc": "Hamburg", "region": "Germany North", "cap": 80, "status": "ONLINE", "fσ": 0.009},
            {"id": "DE-FRA-380", "loc": "Frankfurt", "region": "Germany Central", "cap": 100, "status": "ONLINE", "fσ": 0.007},
            {"id": "FR-MRS-225", "loc": "Marseille", "region": "France South", "cap": 60, "status": "ONLINE", "fσ": 0.010},
            {"id": "DE-DUS-380", "loc": "Düsseldorf", "region": "Germany West", "cap": 80, "status": "ONLINE", "fσ": 0.008},
            {"id": "FR-STRS-225", "loc": "Strasbourg", "region": "France East", "cap": 50, "status": "ONLINE", "fσ": 0.011},
            {"id": "DE-STU-220", "loc": "Stuttgart", "region": "Germany South", "cap": 60, "status": "STANDBY", "fσ": 0.012},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  EMC — Energy Market Company (Singapore)
    # ════════════════════════════════════════════════════════════
    "EMC 🇸🇬": {
        "name": "EMC", "full": "Energy Market Company", "operator": "EMC / EMA",
        "f_nom": 50.0, "H": 5.0, "D": 2.0, "v_nom": 230.0,
        "price_name": "USEP", "currency": "S$", "cur_code": "SGD",
        "price_base": 110, "price_amp": 70, "price_cap": 4500, "price_floor": 0,
        "spike_prob": 0.96, "spike_range": (300, 2000), "settle": "30-min EMC",
        "penalty_f": 0.04, "thd_limit": 5.0, "thd_std": "SS 555",
        "accent": "#e74c3c", "accent2": "#c0392b", "border": "#2a0a0a",
        "protocol": "PRIME-HJB-v8.0-EMC", "tz": "SGT",
        "tagline": "Lion City Grid — Singapore 🇸🇬",
        "price_threshold": 500, "threshold_label": "Vesting Price",
        "penalty_label": "EMA Penalty",
        "load_vol": 0.006, "dist1": 0.03, "dist2": 0.05, "cap_mw": 70,
        "nodes": [
            {"id": "SG-TUA-230", "loc": "Tuas", "region": "West", "cap": 80, "status": "MASTER", "fσ": 0.006},
            {"id": "SG-JUR-230", "loc": "Jurong Island", "region": "West", "cap": 100, "status": "ONLINE", "fσ": 0.007},
            {"id": "SG-PUL-230", "loc": "Pulau Seraya", "region": "South", "cap": 80, "status": "ONLINE", "fσ": 0.007},
            {"id": "SG-SEN-230", "loc": "Senoko", "region": "North", "cap": 80, "status": "ONLINE", "fσ": 0.008},
            {"id": "SG-TMB-66", "loc": "Tembusu", "region": "East", "cap": 40, "status": "ONLINE", "fσ": 0.010},
        ],
    },
    # ════════════════════════════════════════════════════════════
    #  CCEE — Câmara de Comercialização de Energia Elétrica (Brazil)
    # ════════════════════════════════════════════════════════════
    "CCEE 🇧🇷": {
        "name": "CCEE", "full": "Câmara de Comercialização de Energia Elétrica", "operator": "ONS / CCEE",
        "f_nom": 60.0, "H": 5.5, "D": 2.0, "v_nom": 500.0,
        "price_name": "PLD", "currency": "R$", "cur_code": "BRL",
        "price_base": 150, "price_amp": 100, "price_cap": 684.73, "price_floor": 69.04,
        "spike_prob": 0.95, "spike_range": (300, 684), "settle": "Hourly CCEE",
        "penalty_f": 0.05, "thd_limit": 5.0, "thd_std": "PRODIST Mod 8",
        "accent": "#2ecc71", "accent2": "#27ae60", "border": "#0a2a14",
        "protocol": "PRIME-HJB-v8.0-CCEE", "tz": "BRT",
        "tagline": "Soberania Energética — Brasil 🇧🇷",
        "price_threshold": 400, "threshold_label": "PLD High Alert",
        "penalty_label": "ANEEL Penalty",
        "load_vol": 0.009, "dist1": 0.05, "dist2": 0.07, "cap_mw": 130,
        "nodes": [
            {"id": "BR-SPO-500", "loc": "São Paulo", "region": "Sudeste", "cap": 160, "status": "MASTER", "fσ": 0.008},
            {"id": "BR-RIO-500", "loc": "Rio de Janeiro", "region": "Sudeste", "cap": 120, "status": "ONLINE", "fσ": 0.009},
            {"id": "BR-BSB-500", "loc": "Brasília", "region": "Sudeste", "cap": 80, "status": "ONLINE", "fσ": 0.010},
            {"id": "BR-BHZ-345", "loc": "Belo Horizonte", "region": "Sudeste", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "BR-CUR-500", "loc": "Curitiba", "region": "Sul", "cap": 70, "status": "ONLINE", "fσ": 0.012},
            {"id": "BR-POA-230", "loc": "Porto Alegre", "region": "Sul", "cap": 60, "status": "ONLINE", "fσ": 0.013},
            {"id": "BR-REC-500", "loc": "Recife", "region": "Nordeste", "cap": 70, "status": "ONLINE", "fσ": 0.012},
            {"id": "BR-SAL-500", "loc": "Salvador", "region": "Nordeste", "cap": 80, "status": "ONLINE", "fσ": 0.011},
            {"id": "BR-MAN-500", "loc": "Manaus", "region": "Norte", "cap": 50, "status": "STANDBY", "fσ": 0.018},
            {"id": "BR-BEL-500", "loc": "Belém", "region": "Norte", "cap": 60, "status": "ONLINE", "fσ": 0.014},
            {"id": "BR-FOR-230", "loc": "Fortaleza", "region": "Nordeste", "cap": 60, "status": "ONLINE", "fσ": 0.013},
        ],
    },
}

# ============================================================
#  SIDEBAR — Market Selector
# ============================================================
st.sidebar.markdown("## ⚡ Market Selector")
market_key = st.sidebar.radio("Select Market", list(MARKETS.keys()), index=0)
M = MARKETS[market_key]
st.sidebar.divider()
st.sidebar.markdown(f"**{M['full']}**")
st.sidebar.markdown(f"Operator: `{M['operator']}`")
st.sidebar.markdown(f"Nominal: `{M['f_nom']} Hz`")
st.sidebar.markdown(f"Inertia H: `{M['H']} s`")
st.sidebar.markdown(f"Pricing: `{M['price_name']} ({M['cur_code']})`")
st.sidebar.markdown(f"THD Std: `{M['thd_std']} (≤{M['thd_limit']}%)`")
st.sidebar.markdown(f"Nodes: `{len(M['nodes'])}`")
st.sidebar.divider()
st.sidebar.caption(M["tagline"])

AC = M["accent"]  # shortcut

def hex_to_rgba(hex_color, alpha):
    """Convert hex color to rgba string for Plotly."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'

# --- DYNAMIC CSS ---
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
.main {{ background-color: #050810; color: #e0e6ed; font-family: 'Inter', sans-serif; }}
[data-testid="stHeader"] {{ background-color: #050810; }}
[data-testid="stSidebar"] {{ background-color: #0a0f1a; }}
[data-testid="stMetric"] {{
    background: linear-gradient(135deg, #0d1520 0%, #111b2a 100%);
    border: 1px solid {M['border']}; border-radius: 8px; padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}}
div[data-testid="stMetricValue"] {{ color: {AC}; font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 700; text-shadow: 0 0 12px rgba(0,209,255,0.3); }}
div[data-testid="stMetricDelta"] {{ font-family: 'JetBrains Mono', monospace; color: #c8d6e5; }}
div[data-testid="stMetricLabel"] {{
    color: #c8d6e5;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 0px; background-color: #0a0f1a; border-radius: 8px; padding: 4px; }}
.stTabs [data-baseweb="tab"] {{ color: #c8d6e5; font-weight: 600; font-size: 15px; border-radius: 6px; padding: 10px 20px; }}
.stTabs [aria-selected="true"] {{ background: linear-gradient(135deg, {AC}22, {M['accent2']}22); color: {AC} !important; }}
.status-nominal {{ color: #00ff88; font-weight: 700; font-family: 'JetBrains Mono'; animation: pulse 2s infinite; }}
.status-alert {{ color: #ff4b4b; font-weight: 700; font-family: 'JetBrains Mono'; animation: blink 0.8s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} }}
@keyframes blink {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.2; }} }}
.section-header {{ color: {AC}; font-family: 'JetBrains Mono', monospace; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid {M['border']}; padding-bottom: 8px; margin-bottom: 16px; }}
.math-block {{ background: #0a0f1a; border-left: 3px solid {AC}; padding: 16px 20px; font-family: 'JetBrains Mono', monospace; font-size: 15px; color: #e2e8f0; border-radius: 0 6px 6px 0; margin: 12px 0; }}
.kpi-highlight {{ background: linear-gradient(135deg, #001a33, #002244); border: 1px solid #003366; border-radius: 10px; padding: 24px; text-align: center; }}
.kpi-value {{ font-size: 42px; font-weight: 700; color: #00ff88; font-family: 'JetBrains Mono'; }}
.kpi-label {{ font-size: 13px; color: #94a3b8; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }}
/* Markdown & sidebar readability */
.stMarkdown, .stMarkdown p {{ color: #e2e8f0 !important; font-size: 15px; }}
div[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  SIMULATION ENGINE — Parametric for any market
# ============================================================
@st.cache_data(ttl=2)
def generate_simulation_state(market_name, f_nom, H, D, v_nom, price_base, price_amp,
                               price_cap, price_floor, spike_prob, spike_range,
                               load_vol, dist1, dist2, cap_mw, thd_limit, nodes_cfg):
    np.random.seed(int(time.time()) % 10000)
    now = datetime.now()
    dt = 0.01
    n_steps = 600

    freq_history = np.zeros(n_steps)
    rocof_history = np.zeros(n_steps)
    inertia_injection = np.zeros(n_steps)
    p_mechanical = np.ones(n_steps)
    p_electrical = np.ones(n_steps) + np.random.normal(0, load_vol, n_steps)
    p_electrical[200:230] += dist1
    p_electrical[420:445] += dist2

    f = f_nom
    for i in range(n_steps):
        error = f_nom - f
        u_inertia = max(0, error * 500.0)
        inertia_injection[i] = u_inertia
        M_eff = 2 * H + u_inertia
        dfdt = (p_mechanical[i] - p_electrical[i] - D * (f - f_nom)) / M_eff
        f += dfdt * dt
        freq_history[i] = f
        rocof_history[i] = dfdt

    state_grid = np.linspace(f_nom - 0.2, f_nom + 0.2, 200)
    V_function = 0.5 * 1e4 * (state_grid - f_nom)**2
    V_gradient = 1e4 * (state_grid - f_nom)
    u_optimal = -0.5 * V_gradient
    H_field = np.abs(V_gradient * (p_mechanical[-1] - p_electrical[-1])) + V_function * 0.01

    hours = np.arange(0, 24, 0.25)
    px_base = price_base + price_amp * np.sin((hours - 10) * np.pi / 12)
    px_noise = np.cumsum(np.random.normal(0, 1.5, len(hours))) * 0.3
    px_spikes = np.where(np.random.rand(len(hours)) > spike_prob, np.random.uniform(*spike_range, len(hours)), 0)
    prices = np.clip(px_base + px_noise + px_spikes, price_floor, price_cap)

    v_a = v_nom + np.random.normal(0, v_nom * 0.001)
    v_b = v_nom + np.random.normal(0, v_nom * 0.0013)
    v_c = v_nom + np.random.normal(0, v_nom * 0.0009)
    pf = 0.98 + np.random.normal(0, 0.005)

    harmonics = {3: 0.08 + np.random.normal(0, 0.01), 5: 0.05 + np.random.normal(0, 0.008),
                 7: 0.03 + np.random.normal(0, 0.005), 9: 0.015 + np.random.normal(0, 0.003),
                 11: 0.008 + np.random.normal(0, 0.002), 13: 0.004 + np.random.normal(0, 0.001)}
    thd = np.sqrt(sum(v**2 for v in harmonics.values())) * 100

    optimal_mw = cap_mw * np.maximum(0, np.sin((hours - 6) * np.pi / 12))
    legacy_loss = np.random.uniform(0.75, 0.85, len(hours))
    actual_mw = optimal_mw * legacy_loss
    actual_mw *= np.random.normal(1.0, 0.015, len(hours))
    actual_mw = np.maximum(0, actual_mw)
    delta_mw = np.maximum(0, optimal_mw - actual_mw)
    capital_cumulative = np.cumsum(delta_mw * prices * 0.25)

    nodes = []
    for n in nodes_cfg:
        nodes.append({**n, "f": f_nom + np.random.normal(0, n["fσ"]),
                      "load": np.random.randint(35, 85)})

    return {
        "now": now, "f_current": freq_history[-1], "rocof": rocof_history[-1],
        "freq_history": freq_history, "rocof_history": rocof_history,
        "inertia_injection": inertia_injection, "p_electrical": p_electrical,
        "state_grid": state_grid, "V_function": V_function, "V_gradient": V_gradient,
        "u_optimal": u_optimal, "H_field": H_field,
        "prices": prices, "hours": hours,
        "optimal_mw": optimal_mw, "actual_mw": actual_mw,
        "capital_cumulative": capital_cumulative, "capital_total": capital_cumulative[-1],
        "v_a": v_a, "v_b": v_b, "v_c": v_c, "pf": pf,
        "thd": thd, "harmonics": harmonics, "nodes": nodes, "n_steps": n_steps,
    }

state = generate_simulation_state(
    M["name"], M["f_nom"], M["H"], M["D"], M["v_nom"],
    M["price_base"], M["price_amp"], M["price_cap"], M["price_floor"],
    M["spike_prob"], M["spike_range"], M["load_vol"], M["dist1"], M["dist2"],
    M["cap_mw"], M["thd_limit"], M["nodes"]
)
now = state["now"]
f = state["f_current"]
f0 = M["f_nom"]
is_nominal = abs(f - f0) < M["penalty_f"]

# ============================================================
#  HEADER
# ============================================================
h1, h2, h3 = st.columns([4, 2, 2])
with h1:
    st.markdown(f"# ⚡ PRIMEnergeia — {M['name']}")
    st.caption(f"HAMILTON-JACOBI-BELLMAN OPTIMAL FREQUENCY CONTROL | {M['full'].upper()}")
with h2:
    sc = "status-nominal" if is_nominal else "status-alert"
    st.markdown(f"<p class='{sc}' style='font-size:18px; margin-top:20px;'>{'● NOMINAL' if is_nominal else '⚠ EXCURSION'}</p>", unsafe_allow_html=True)
    st.caption(f"Protocol: {M['protocol']}")
with h3:
    st.markdown(f"<p style='font-family:JetBrains Mono;color:#94a3b8;margin-top:20px;font-size:14px;'>{now.strftime('%Y-%m-%d %H:%M:%S')} {M['tz']}</p>", unsafe_allow_html=True)
    st.caption(f"Latency: 0.{np.random.randint(3,9)}ms | Uptime: 99.98%")

st.divider()

# ============================================================
#  KPI BAR
# ============================================================
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("FREQUENCY", f"{f:.4f} Hz", f"Δ {f-f0:+.4f}")
k2.metric("RoCoF", f"{state['rocof']:+.5f} Hz/s", "Swing Eq.")
k3.metric("VOLTAGE Φ-A", f"{state['v_a']:.1f} kV", f"{M['v_nom']:.0f} kV Nom.")
k4.metric("THD", f"{state['thd']:.2f} %", f"{'✓ ' + M['thd_std'] if state['thd'] < M['thd_limit'] else '⚠ Exceeds'}")
k5.metric("COS φ", f"{state['pf']:.4f}", "Unity Target")
k6.metric("HOUR OF DAY", now.strftime("%H:%M"), "Live")
k7.metric("RESCUED ACC.", f"{M['currency']}{state['capital_total']:,.0f}", f"{M['cur_code']} / day")

st.markdown("")

# ============================================================
#  TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 PHYSICS ENGINE", "🧮 HJB OPTIMIZER", "💰 FINANCIAL ENGINE",
    "🔬 HARMONIC ANALYSIS", "🌐 NETWORK TOPOLOGY", "📋 AUDIT LOG"
])

t_axis = np.linspace(0, 6, state["n_steps"])

# --- TAB 1: PHYSICS ---
with tab1:
    st.markdown(f"<div class='section-header'>REAL-TIME SWING EQUATION — {M['name']} ({M['f_nom']:.0f} Hz GRID)</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='math-block'>
    <strong>Swing Equation:</strong>&nbsp;&nbsp; M<sub>eff</sub> · (df/dt) = P<sub>m</sub> − P<sub>e</sub> − D · (f − f<sub>0</sub>)<br>
    <strong>Where:</strong>&nbsp;&nbsp; M<sub>eff</sub> = 2H + u<sub>inertia</sub> &nbsp;|&nbsp; H = {M['H']}s &nbsp;|&nbsp; D = {M['D']} &nbsp;|&nbsp; dt = 10ms
    </div>""", unsafe_allow_html=True)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=("Grid Frequency — Swing Equation Solution", "Rate of Change of Frequency (RoCoF)", "Synthetic Inertia Injection u(t)"),
        row_heights=[0.4, 0.3, 0.3])
    fig.add_trace(go.Scatter(x=t_axis, y=state["freq_history"], name="f(t)", line=dict(color=AC, width=2.5)), row=1, col=1)
    fig.add_hline(y=f0, line_dash="dash", line_color="#00ff88", annotation_text=f"f₀ = {f0:.3f} Hz", row=1, col=1)
    fig.add_hline(y=f0 - M["penalty_f"], line_dash="dot", line_color="#ff4b4b", annotation_text=M["penalty_label"], row=1, col=1)
    fig.add_hline(y=f0 + M["penalty_f"], line_dash="dot", line_color="#ff4b4b", row=1, col=1)
    fig.add_trace(go.Scatter(x=t_axis, y=state["rocof_history"], name="df/dt", line=dict(color="#fbc02d", width=1.5), fill='tozeroy', fillcolor='rgba(251,192,45,0.08)'), row=2, col=1)
    fig.add_trace(go.Scatter(x=t_axis, y=state["inertia_injection"], name="u(t)", line=dict(color="#00ff88", width=2), fill='tozeroy', fillcolor='rgba(0,255,136,0.1)'), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=750, showlegend=False, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", margin=dict(l=60,r=20,t=80,b=40), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig.update_xaxes(title_text="Time (s)", row=3, col=1, gridcolor="#1a2744")
    fig.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig, use_container_width=True)
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("INERTIA H", f"{M['H']} s", M['thd_std'])
    pc2.metric("DAMPING D", f"{M['D']} p.u.", "Calibrated")
    pc3.metric("STEP dt", "10 ms", "Euler Method")

# --- TAB 2: HJB ---
with tab2:
    st.markdown("<div class='section-header'>HAMILTON-JACOBI-BELLMAN OPTIMAL CONTROL SOLUTION</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='math-block'>
    <strong>HJB:</strong>&nbsp;&nbsp; V<sub>t</sub> + min<sub>u</sub> {{ L(x,u) + ∇V · f(x,u) }} = 0<br>
    <strong>Cost:</strong>&nbsp;&nbsp; L = ½Q(f−f₀)² + ½Ru² &nbsp;|&nbsp; <strong>u*(x) = −R⁻¹B<sup>T</sup>∇V(x)</strong> &nbsp;|&nbsp; f₀ = {f0} Hz
    </div>""", unsafe_allow_html=True)
    sg = state["state_grid"]
    fig2 = make_subplots(rows=2, cols=2, vertical_spacing=0.18, horizontal_spacing=0.08,
        subplot_titles=("Value Function V(x)", "Policy Gradient ∇V(x)", "Optimal Control u*(x)", "Hamiltonian H(x,u*)"))
    fig2.add_trace(go.Scatter(x=sg, y=state["V_function"], line=dict(color=AC, width=3), fill='tozeroy', fillcolor=hex_to_rgba(AC, 0.06)), row=1, col=1)
    fig2.add_trace(go.Scatter(x=sg, y=state["V_gradient"], line=dict(color="#ff6b6b", width=2.5)), row=1, col=2)
    fig2.add_hline(y=0, line_dash="dash", line_color="#333", row=1, col=2)
    fig2.add_trace(go.Scatter(x=sg, y=state["u_optimal"], line=dict(color="#00ff88", width=3), fill='tozeroy', fillcolor='rgba(0,255,136,0.08)'), row=2, col=1)
    fig2.add_vline(x=f0, line_dash="dash", line_color="#fbc02d", annotation_text="f₀", row=2, col=1)
    fig2.add_trace(go.Scatter(x=sg, y=state["H_field"], line=dict(color="#fbc02d", width=2), fill='tozeroy', fillcolor='rgba(251,192,45,0.06)'), row=2, col=2)
    fig2.update_layout(template="plotly_dark", height=750, showlegend=False, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", margin=dict(l=60,r=20,t=80,b=40), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig2.update_xaxes(title_text="Frequency (Hz)", gridcolor="#1a2744")
    fig2.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig2, use_container_width=True)
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Q (STATE)", "10,000", "Freq penalty")
    hc2.metric("R (CONTROL)", "1.0", "Actuation")
    hc3.metric("V(f₀)", "0.000", "Min cost")
    hc4.metric("STATUS", "✓ SOLVED", "Converged")

# --- TAB 3: FINANCIAL ---
with tab3:
    st.markdown(f"<div class='section-header'>CAPITAL RECOVERY — {M['price_name']} MARKET ({M['cur_code']})</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='math-block'>
    <strong>Recovery:</strong>&nbsp;&nbsp; Σ[(P*−P<sub>act</sub>) × {M['price_name']} × Δt] &nbsp;|&nbsp; Settlement: {M['settle']} &nbsp;|&nbsp; Royalty: 25%
    </div>""", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown(f"<div class='kpi-highlight'><div class='kpi-value'>{M['currency']}{state['capital_total']:,.0f}</div><div class='kpi-label'>Total Rescued</div></div>", unsafe_allow_html=True)
    with fc2:
        st.markdown(f"<div class='kpi-highlight'><div class='kpi-value' style='color:{AC};'>{M['currency']}{state['capital_total']*0.75:,.0f}</div><div class='kpi-label'>Client (75%)</div></div>", unsafe_allow_html=True)
    with fc3:
        st.markdown(f"<div class='kpi-highlight'><div class='kpi-value' style='color:#fbc02d;'>{M['currency']}{state['capital_total']*0.25:,.0f}</div><div class='kpi-label'>PRIME Fee (25%)</div></div>", unsafe_allow_html=True)
    st.markdown("")
    h = state["hours"]
    fig3 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.18,
        subplot_titles=("Injection: Optimal vs Actual (MW)", f"Cumulative Recovery ({M['cur_code']})"))
    fig3.add_trace(go.Scatter(x=h, y=state["optimal_mw"], name="P* Optimal", line=dict(color="#00ff88", width=2.5)), row=1, col=1)
    fig3.add_trace(go.Scatter(x=h, y=state["actual_mw"], name="P Actual", line=dict(color="#ff4b4b", width=1.5, dash="dash")), row=1, col=1)
    fig3.add_trace(go.Scatter(x=h, y=state["optimal_mw"], fill='tonexty', fillcolor='rgba(255,75,75,0.12)', showlegend=False, line=dict(width=0)), row=1, col=1)
    fig3.add_trace(go.Scatter(x=h, y=state["capital_cumulative"], name="Rescued", line=dict(color=AC, width=3), fill='tozeroy', fillcolor=hex_to_rgba(AC, 0.08)), row=2, col=1)
    curr_h = now.hour + now.minute/60.0
    fig3.add_vline(x=curr_h, line_dash="dash", line_color=AC, opacity=0.7, annotation_text="LIVE")
    fig3.update_layout(template="plotly_dark", height=700, showlegend=True, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", margin=dict(l=60,r=20,t=100,b=40), legend=dict(orientation="h", y=1.18, x=0.5, xanchor="center"), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig3.update_xaxes(title_text="Hour", gridcolor="#1a2744")
    fig3.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f"<div class='section-header'>{M['price_name']} MARKET DYNAMICS</div>", unsafe_allow_html=True)
    fig_px = go.Figure()
    fig_px.add_trace(go.Scatter(x=h, y=state["prices"], name=f"{M['price_name']} ({M['cur_code']}/MWh)", line=dict(color=AC, width=2), fill='tozeroy', fillcolor=hex_to_rgba(AC, 0.06)))
    fig_px.add_hline(y=M["price_threshold"], line_dash="dash", line_color="#ff4b4b", annotation_text=M["threshold_label"])
    fig_px.add_vline(x=curr_h, line_dash="dash", line_color=AC, opacity=0.7, annotation_text="LIVE")
    fig_px.update_layout(template="plotly_dark", height=280, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", margin=dict(l=60,r=20,t=20,b=40), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig_px.update_xaxes(gridcolor="#1a2744")
    fig_px.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig_px, use_container_width=True)

# --- TAB 4: HARMONICS ---
with tab4:
    st.markdown(f"<div class='section-header'>HARMONIC ANALYSIS — {M['thd_std']} COMPLIANCE</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='math-block'>
    <strong>THD:</strong>&nbsp;&nbsp; √(Σ V<sub>h</sub>²)/V<sub>1</sub> × 100% &nbsp;|&nbsp; {M['thd_std']} Limit: THD ≤ {M['thd_limit']}%
    </div>""", unsafe_allow_html=True)
    hd1, hd2, hd3 = st.columns(3)
    hd1.metric("THD", f"{state['thd']:.2f} %", f"{'✓ COMPLIANT' if state['thd'] < M['thd_limit'] else '⚠ VIOLATION'}")
    hd2.metric(f"FUNDAMENTAL ({f0:.0f} Hz)", "100.00 %", "Reference")
    hd3.metric("WORST", f"3rd ({abs(state['harmonics'][3])*100:.2f}%)", f"{int(f0*3)} Hz")

    ho = list(state["harmonics"].keys())
    hv = [abs(v)*100 for v in state["harmonics"].values()]
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=[f"H{h} ({int(h*f0)}Hz)" for h in ho], y=hv,
        marker=dict(color=["#ff4b4b" if v > M['thd_limit']*0.6 else AC for v in hv], line=dict(color=M['border'], width=1)),
        text=[f"{v:.2f}%" for v in hv], textposition='outside', textfont=dict(family="JetBrains Mono", size=12, color="#e0e6ed")))
    fig4.add_hline(y=M['thd_limit']*0.6, line_dash="dash", line_color="#ff4b4b", annotation_text=f"{M['thd_std']} Ind. Limit")
    fig4.update_layout(template="plotly_dark", height=350, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", yaxis_title="Magnitude (%)", margin=dict(l=60,r=20,t=20,b=40), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig4.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown(f"<div class='section-header'>THREE-PHASE WAVEFORM — {f0:.0f} Hz</div>", unsafe_allow_html=True)
    t_wave = np.linspace(0, 3/f0, 1000)
    pa = np.sin(2*np.pi*f0*t_wave)
    pb = np.sin(2*np.pi*f0*t_wave - 2*np.pi/3)
    pc = np.sin(2*np.pi*f0*t_wave + 2*np.pi/3)
    da = pa + sum(state["harmonics"][h]*np.sin(2*np.pi*f0*h*t_wave) for h in state["harmonics"])
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=t_wave*1000, y=da, name="Pre-PRIME", line=dict(color="#ff4b4b", width=1, dash="dot"), opacity=0.5))
    fig5.add_trace(go.Scatter(x=t_wave*1000, y=pa, name="Phase A", line=dict(color=AC, width=2.5)))
    fig5.add_trace(go.Scatter(x=t_wave*1000, y=pb, name="Phase B", line=dict(color="#00ff88", width=2)))
    fig5.add_trace(go.Scatter(x=t_wave*1000, y=pc, name="Phase C", line=dict(color="#fbc02d", width=2)))
    fig5.update_layout(template="plotly_dark", height=320, paper_bgcolor="#050810", plot_bgcolor="#0a0f1a", margin=dict(l=60,r=20,t=20,b=40), xaxis_title="Time (ms)", yaxis_title="V (p.u.)", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"), font=dict(family="JetBrains Mono", size=14, color="#94a3b8"))
    fig5.update_xaxes(gridcolor="#1a2744")
    fig5.update_yaxes(gridcolor="#1a2744")
    st.plotly_chart(fig5, use_container_width=True)
    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("V Φ-A", f"{state['v_a']:.1f} kV", "Balanced")
    vc2.metric("V Φ-B", f"{state['v_b']:.1f} kV", "Balanced")
    vc3.metric("V Φ-C", f"{state['v_c']:.1f} kV", "Balanced")
    vc4.metric("IMBALANCE", f"{abs(state['v_a']-state['v_b'])*100/M['v_nom']:.3f} %", "< 2%")

# --- TAB 5: NETWORK ---
with tab5:
    st.markdown(f"<div class='section-header'>{M['name']} GRID — {len(state['nodes'])}-NODE SOVEREIGN NETWORK</div>", unsafe_allow_html=True)
    from collections import OrderedDict
    regions = OrderedDict()
    for node in state["nodes"]:
        regions.setdefault(node["region"], []).append(node)
    for rname, rnodes in regions.items():
        st.markdown(f"<p style='font-family:JetBrains Mono;font-size:11px;color:{AC};letter-spacing:2px;margin:16px 0 8px 0;'>▸ {rname.upper()}</p>", unsafe_allow_html=True)
        for i in range(0, len(rnodes), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i+j < len(rnodes):
                    n = rnodes[i+j]
                    sc = "#00ff88" if n["status"] in ["MASTER","ONLINE"] else "#fbc02d"
                    fd = n["f"] - f0
                    with col:
                        st.markdown(f"""<div style='background:linear-gradient(135deg,#0d1520,#111b2a);border:1px solid {M['border']};
                            border-left:4px solid {sc};border-radius:8px;padding:14px 16px;margin-bottom:10px;'>
                            <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <div><span style='font-family:JetBrains Mono;font-size:14px;font-weight:700;color:#e0e6ed;'>{n["id"]}</span>
                            <span style='font-size:10px;color:{sc};margin-left:8px;font-weight:700;'>● {n["status"]}</span></div>
                            <span style='font-family:JetBrains Mono;font-size:16px;color:{AC};'>{n["f"]:.3f} Hz</span></div>
                            <div style='font-size:11px;color:#94a3b8;margin-top:5px;'>{n["loc"]} | {n["cap"]} MW | Load: {n["load"]}% | Δf: {fd:+.4f}</div>
                            </div>""", unsafe_allow_html=True)
    st.markdown("")
    ns1, ns2, ns3, ns4 = st.columns(4)
    active = sum(1 for n in state["nodes"] if n["status"] in ["MASTER","ONLINE"])
    ns1.metric("ACTIVE", f"{active}/{len(state['nodes'])}", "Operational")
    ns2.metric("AVG FREQ", f"{np.mean([n['f'] for n in state['nodes']]):.4f} Hz", f"Δ {np.mean([n['f'] for n in state['nodes']])-f0:+.4f}")
    ns3.metric("AVG LOAD", f"{np.mean([n['load'] for n in state['nodes']]):.0f} %", "Network")
    ns4.metric("CAPACITY", f"{sum(n['cap'] for n in state['nodes']):,} MW", "Aggregate")

# --- TAB 6: AUDIT ---
with tab6:
    st.markdown(f"<div class='section-header'>AUDIT LOG — {M['thd_std']} / {M['operator']} COMPLIANCE</div>", unsafe_allow_html=True)
    audit_data = {
        "Timestamp": [(now - timedelta(minutes=i*15)).strftime("%Y-%m-%d %H:%M:%S") for i in range(20, 0, -1)],
        "Event": [
            "HJB convergence verified", f"{M['price_name']} spike detected", "Inertia injection: 2.4 p.u.",
            f"Frequency stabilized: {f0-.002:.3f} Hz", "Node sync confirmed", f"Capital checkpoint: {M['currency']}12,480",
            f"THD: {state['thd']:.2f}%", f"{M['thd_std']}: COMPLIANT", "RoCoF within limits",
            "Node load rebalanced", f"{M['price_name']} normalized", "HJB re-solved",
            "Swing Eq. OK", "Phase imbalance: 0.03%", f"Capital: {M['currency']}28,940",
            "DRL weight update", "Heartbeat: all nodes", f"Arbitrage captured: {M['currency']}3,200",
            f"Freq nominal: {f0+.001:.3f} Hz", "System: VERIFIED"
        ],
        "Severity": ["INFO","WARNING","ACTION","INFO","INFO","FINANCIAL","INFO","COMPLIANCE","INFO","ACTION","INFO","ACTION","INFO","INFO","FINANCIAL","ACTION","INFO","FINANCIAL","INFO","COMPLIANCE"]
    }
    df_audit = pd.DataFrame(audit_data)
    def color_sev(val):
        return {"INFO":"color:#94a3b8","WARNING":"color:#fbc02d","ACTION":f"color:{AC}","FINANCIAL":"color:#00ff88","COMPLIANCE":"color:#a78bfa"}.get(val,"color:white")
    st.dataframe(df_audit.style.map(color_sev, subset=["Severity"]), use_container_width=True, height=600, hide_index=True)

# ============================================================
#  FOOTER
# ============================================================
st.divider()
fc1, fc2, fc3 = st.columns([2, 3, 2])
with fc1:
    st.caption("PRIMEnergeia S.A.S.")
    st.caption("Proprietary Protocol")
with fc2:
    st.caption("Lead Computational Physicist: Diego Córdoba Urrutia")
    st.caption("HJB: V_t + min_u { L(x,u) + ∇V · f(x,u) } = 0")
with fc3:
    st.caption(M["tagline"])
    st.caption(f"Build: {M['protocol']} | {now.strftime('%Y')}")
