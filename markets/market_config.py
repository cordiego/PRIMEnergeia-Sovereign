"""
PRIMEnergeia Markets — Shared Configuration Module
===================================================
Defines market-specific parameters for ERCOT, SEN, and MIBEL grids.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict


@dataclass
class MarketConfig:
    """Configuration for an electricity market."""
    # Identity
    name: str
    full_name: str
    operator: str
    country: str
    flag: str

    # Grid Physics
    f_nominal: float        # Hz
    inertia_H: float        # seconds
    damping_D: float        # p.u.
    dt: float = 0.01        # integration step (s)

    # Market
    currency: str = "USD"
    currency_symbol: str = "$"
    price_mechanism: str = "LMP"
    price_unit: str = "USD/MWh"
    price_base: float = 42.0
    price_amplitude: float = 22.0
    price_cap: float = 5000.0
    price_floor: float = 0.0
    spike_probability: float = 0.05
    spike_range: Tuple[float, float] = (80, 200)
    settlement_minutes: int = 15

    # Regulatory
    penalty_threshold: float = 0.05  # Hz deviation before penalties
    thd_limit: float = 5.0           # %
    thd_standard: str = "IEEE 519"
    voltage_nominal: float = 115.0   # kV

    # Dashboard Theme
    accent_color: str = "#00d1ff"
    accent_color_secondary: str = "#0066ff"
    success_color: str = "#00ff88"
    warning_color: str = "#fbc02d"
    danger_color: str = "#ff4b4b"
    bg_primary: str = "#050810"
    bg_secondary: str = "#0a0f1a"
    border_color: str = "#1a2744"

    # Branding
    protocol_version: str = "PRIME-HJB-v8.0"
    tagline: str = ""

    # Nodes
    nodes: List[Dict] = field(default_factory=list)


# ============================================================
#  ERCOT — Electric Reliability Council of Texas
# ============================================================

ERCOT_NODES = [
    # (id, location, zone, capacity_MW, voltage_kV)
    # — Houston Zone —
    {"id": "HOU-345-01", "loc": "Houston Central", "region": "Houston", "cap": 120, "kv": 345},
    {"id": "HOU-345-02", "loc": "Baytown", "region": "Houston", "cap": 100, "kv": 345},
    {"id": "HOU-138-03", "loc": "Galveston", "region": "Houston", "cap": 60, "kv": 138},
    # — North Zone —
    {"id": "NTH-345-01", "loc": "Dallas–Fort Worth", "region": "North", "cap": 120, "kv": 345},
    {"id": "NTH-345-02", "loc": "Denton", "region": "North", "cap": 80, "kv": 345},
    {"id": "NTH-138-03", "loc": "Waco", "region": "North", "cap": 60, "kv": 138},
    # — South Zone —
    {"id": "STH-345-01", "loc": "San Antonio", "region": "South", "cap": 100, "kv": 345},
    {"id": "STH-345-02", "loc": "Corpus Christi", "region": "South", "cap": 80, "kv": 345},
    {"id": "STH-138-03", "loc": "Laredo", "region": "South", "cap": 50, "kv": 138},
    # — West Zone —
    {"id": "WST-345-01", "loc": "Midland–Odessa", "region": "West", "cap": 100, "kv": 345},
    {"id": "WST-345-02", "loc": "Abilene", "region": "West", "cap": 80, "kv": 345},
    {"id": "WST-138-03", "loc": "San Angelo", "region": "West", "cap": 60, "kv": 138},
    # — Far West Zone —
    {"id": "FWS-345-01", "loc": "El Paso", "region": "Far West", "cap": 80, "kv": 345},
    {"id": "FWS-138-02", "loc": "Pecos", "region": "Far West", "cap": 60, "kv": 138},
    # — Coast Zone —
    {"id": "CST-345-01", "loc": "Victoria", "region": "Coast", "cap": 80, "kv": 345},
    {"id": "CST-138-02", "loc": "Bay City", "region": "Coast", "cap": 60, "kv": 138},
    {"id": "CST-138-03", "loc": "Freeport", "region": "Coast", "cap": 50, "kv": 138},
    # — Panhandle Zone —
    {"id": "PNH-345-01", "loc": "Amarillo", "region": "Panhandle", "cap": 80, "kv": 345},
    {"id": "PNH-138-02", "loc": "Lubbock", "region": "Panhandle", "cap": 60, "kv": 138},
    # — East Zone —
    {"id": "EST-345-01", "loc": "Beaumont", "region": "East", "cap": 80, "kv": 345},
    {"id": "EST-345-02", "loc": "Tyler", "region": "East", "cap": 80, "kv": 345},
    {"id": "EST-138-03", "loc": "Lufkin", "region": "East", "cap": 50, "kv": 138},
    # — Austin Zone (part of South) —
    {"id": "AUS-345-01", "loc": "Austin", "region": "South", "cap": 100, "kv": 345},
    {"id": "AUS-138-02", "loc": "Georgetown", "region": "South", "cap": 60, "kv": 138},
    {"id": "AUS-138-03", "loc": "Round Rock", "region": "South", "cap": 50, "kv": 138},
]

ERCOT_CONFIG = MarketConfig(
    name="ERCOT",
    full_name="Electric Reliability Council of Texas",
    operator="ERCOT ISO",
    country="United States",
    flag="🇺🇸",
    f_nominal=60.0,
    inertia_H=4.5,
    damping_D=1.8,
    currency="USD",
    currency_symbol="$",
    price_mechanism="LMP",
    price_unit="USD/MWh",
    price_base=35.0,
    price_amplitude=30.0,
    price_cap=5000.0,
    price_floor=-50.0,
    spike_probability=0.04,
    spike_range=(200, 2000),
    settlement_minutes=5,
    penalty_threshold=0.03,
    thd_limit=5.0,
    thd_standard="IEEE 519",
    voltage_nominal=345.0,
    accent_color="#ff6b35",
    accent_color_secondary="#cc4400",
    protocol_version="PRIME-HJB-v8.0-ERCOT",
    tagline="Energy Sovereignty for Texas ⚡",
    nodes=ERCOT_NODES,
)


# ============================================================
#  SEN — Sistema Eléctrico Nacional (Mexico)
# ============================================================

SEN_NODES = [
    # — Central —
    {"id": "05-VZA-400", "loc": "Valle de México", "region": "Central", "cap": 100, "kv": 400, "source": "public_cenace_data"},
    {"id": "01-QRO-230", "loc": "Querétaro", "region": "Central", "cap": 80, "kv": 230},
    {"id": "01-TUL-400", "loc": "Tula, Hidalgo", "region": "Central", "cap": 100, "kv": 400},
    {"id": "06-SLP-400", "loc": "San Luis Potosí", "region": "Central", "cap": 100, "kv": 400},
    # — Oriental —
    {"id": "02-PUE-400", "loc": "Puebla", "region": "Oriental", "cap": 100, "kv": 400},
    {"id": "02-VER-230", "loc": "Veracruz", "region": "Oriental", "cap": 80, "kv": 230},
    {"id": "02-OAX-230", "loc": "Oaxaca", "region": "Oriental", "cap": 80, "kv": 230},
    {"id": "02-TEH-400", "loc": "Tehuantepec", "region": "Oriental", "cap": 100, "kv": 400},
    # — Occidental —
    {"id": "03-GDL-400", "loc": "Guadalajara", "region": "Occidental", "cap": 100, "kv": 400},
    {"id": "03-MAN-400", "loc": "Manzanillo", "region": "Occidental", "cap": 100, "kv": 400},
    {"id": "03-AGS-230", "loc": "Aguascalientes", "region": "Occidental", "cap": 80, "kv": 230},
    {"id": "03-COL-115", "loc": "Colima", "region": "Occidental", "cap": 40, "kv": 115},
    # — Noreste —
    {"id": "04-MTY-400", "loc": "Monterrey", "region": "Noreste", "cap": 100, "kv": 400},
    {"id": "04-TAM-230", "loc": "Tampico", "region": "Noreste", "cap": 80, "kv": 230},
    {"id": "04-SAL-400", "loc": "Saltillo", "region": "Noreste", "cap": 100, "kv": 400},
    # — Norte —
    {"id": "05-CHI-400", "loc": "Chihuahua", "region": "Norte", "cap": 100, "kv": 400},
    {"id": "05-LAG-230", "loc": "Gómez Palacio", "region": "Norte", "cap": 80, "kv": 230},
    {"id": "05-DGO-230", "loc": "Durango", "region": "Norte", "cap": 60, "kv": 230},
    {"id": "05-JRZ-230", "loc": "Cd. Juárez", "region": "Norte", "cap": 80, "kv": 230},
    # — Noroeste —
    {"id": "07-HER-230", "loc": "Hermosillo", "region": "Noroeste", "cap": 80, "kv": 230},
    {"id": "07-NAV-230", "loc": "Navojoa", "region": "Noroeste", "cap": 60, "kv": 230},
    {"id": "07-CUM-115", "loc": "Cd. Obregón", "region": "Noroeste", "cap": 40, "kv": 115},
    {"id": "07-GUY-230", "loc": "Guaymas", "region": "Noroeste", "cap": 60, "kv": 230},
    {"id": "07-CUL-230", "loc": "Culiacán", "region": "Noroeste", "cap": 80, "kv": 230},
    # — Baja California —
    {"id": "08-MXL-230", "loc": "Mexicali", "region": "Baja California", "cap": 80, "kv": 230},
    {"id": "08-ENS-230", "loc": "Ensenada", "region": "Baja California", "cap": 80, "kv": 230},
    {"id": "08-TIJ-230", "loc": "Tijuana", "region": "Baja California", "cap": 80, "kv": 230},
    # — Baja California Sur —
    {"id": "09-LAP-115", "loc": "La Paz", "region": "BCS", "cap": 40, "kv": 115},
    # — Peninsular —
    {"id": "10-MER-230", "loc": "Mérida", "region": "Peninsular", "cap": 80, "kv": 230},
    {"id": "10-CAN-230", "loc": "Cancún", "region": "Peninsular", "cap": 80, "kv": 230},
]

SEN_CONFIG = MarketConfig(
    name="SEN",
    full_name="Sistema Eléctrico Nacional",
    operator="CENACE",
    country="México",
    flag="🇲🇽",
    f_nominal=60.0,
    inertia_H=5.0,
    damping_D=2.0,
    currency="USD",
    currency_symbol="$",
    price_mechanism="PML",
    price_unit="USD/MWh",
    price_base=42.0,
    price_amplitude=22.0,
    price_cap=350.0,
    price_floor=28.0,
    spike_probability=0.05,
    spike_range=(80, 200),
    settlement_minutes=15,
    penalty_threshold=0.05,
    thd_limit=5.0,
    thd_standard="Código de Red",
    voltage_nominal=115.0,
    accent_color="#00d1ff",
    accent_color_secondary="#0066ff",
    protocol_version="PRIME-HJB-v8.0-SEN",
    tagline="Soberanía Energética para México 🇲🇽",
    nodes=SEN_NODES,
)


# ============================================================
#  MIBEL — Mercado Ibérico de Electricidad
# ============================================================

MIBEL_NODES = [
    # — Spain: North —
    {"id": "ES-BIL-400", "loc": "Bilbao", "region": "Spain North", "cap": 100, "kv": 400},
    {"id": "ES-ZAR-400", "loc": "Zaragoza", "region": "Spain North", "cap": 80, "kv": 400},
    {"id": "ES-BCN-400", "loc": "Barcelona", "region": "Spain North", "cap": 120, "kv": 400},
    # — Spain: Central —
    {"id": "ES-MAD-400", "loc": "Madrid", "region": "Spain Central", "cap": 150, "kv": 400},
    {"id": "ES-VAL-400", "loc": "Valencia", "region": "Spain Central", "cap": 100, "kv": 400},
    {"id": "ES-CLM-220", "loc": "Ciudad Real", "region": "Spain Central", "cap": 60, "kv": 220},
    # — Spain: South —
    {"id": "ES-SEV-400", "loc": "Sevilla", "region": "Spain South", "cap": 100, "kv": 400},
    {"id": "ES-MAL-400", "loc": "Málaga", "region": "Spain South", "cap": 80, "kv": 400},
    {"id": "ES-ALM-220", "loc": "Almería", "region": "Spain South", "cap": 60, "kv": 220},
    {"id": "ES-GRA-220", "loc": "Granada", "region": "Spain South", "cap": 60, "kv": 220},
    # — Spain: Northwest —
    {"id": "ES-COR-400", "loc": "A Coruña", "region": "Spain Northwest", "cap": 80, "kv": 400},
    {"id": "ES-LEO-220", "loc": "León", "region": "Spain Northwest", "cap": 60, "kv": 220},
    # — Spain: Islands —
    {"id": "ES-PMI-220", "loc": "Palma de Mallorca", "region": "Balearic Islands", "cap": 40, "kv": 220},
    {"id": "ES-TFE-220", "loc": "Tenerife", "region": "Canary Islands", "cap": 40, "kv": 220},
    {"id": "ES-LPA-220", "loc": "Las Palmas", "region": "Canary Islands", "cap": 40, "kv": 220},
    # — Portugal: North —
    {"id": "PT-PRT-400", "loc": "Porto", "region": "Portugal North", "cap": 80, "kv": 400},
    {"id": "PT-BRG-220", "loc": "Braga", "region": "Portugal North", "cap": 50, "kv": 220},
    # — Portugal: South —
    {"id": "PT-LIS-400", "loc": "Lisboa", "region": "Portugal South", "cap": 100, "kv": 400},
    {"id": "PT-FAR-220", "loc": "Faro", "region": "Portugal South", "cap": 50, "kv": 220},
    {"id": "PT-SET-220", "loc": "Setúbal", "region": "Portugal South", "cap": 50, "kv": 220},
]

MIBEL_CONFIG = MarketConfig(
    name="MIBEL",
    full_name="Mercado Ibérico de Electricidad",
    operator="OMIE / REE / REN",
    country="Spain & Portugal",
    flag="🇪🇸🇵🇹",
    f_nominal=50.0,
    inertia_H=6.0,
    damping_D=2.5,
    currency="EUR",
    currency_symbol="€",
    price_mechanism="Pool Price",
    price_unit="EUR/MWh",
    price_base=55.0,
    price_amplitude=35.0,
    price_cap=3000.0,
    price_floor=0.0,
    spike_probability=0.03,
    spike_range=(150, 500),
    settlement_minutes=60,
    penalty_threshold=0.04,
    thd_limit=8.0,
    thd_standard="EN 50160",
    voltage_nominal=220.0,
    accent_color="#e8c547",
    accent_color_secondary="#c9a020",
    protocol_version="PRIME-HJB-v8.0-MIBEL",
    tagline="Soberanía Energética Ibérica ⚡",
    nodes=MIBEL_NODES,
)


# Quick access dict
ALL_MARKETS = {
    "ERCOT": ERCOT_CONFIG,
    "SEN": SEN_CONFIG,
    "MIBEL": MIBEL_CONFIG,
}
