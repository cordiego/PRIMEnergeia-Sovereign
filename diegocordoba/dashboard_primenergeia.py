import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json, os, time
import urllib.request, urllib.parse
from datetime import datetime

def send_telegram_notification(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    telemetry_dir = os.path.expanduser("~/.prime_telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    log_file = os.path.join(telemetry_dir, f"notifications_{datetime.now().strftime('%Y%m%d')}.jsonl")
    
    log_entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "channel": "telegram",
        "message": message,
        "error": None
    }
    
    if not bot_token or not chat_id:
        log_entry["error"] = "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"
        with open(log_file, "a") as f: f.write(json.dumps(log_entry) + "\n")
        return False, log_entry["error"]
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if not result.get("ok"):
                log_entry["error"] = f"API Error: {result}"
            with open(log_file, "a") as f: f.write(json.dumps(log_entry) + "\n")
            return result.get("ok", False), "Success" if result.get("ok") else "API Error"
    except Exception as e:
        log_entry["error"] = str(e)
        with open(log_file, "a") as f: f.write(json.dumps(log_entry) + "\n")
        return False, str(e)

st.set_page_config(page_title="PRIMEnergeia S.A.S. Control", layout="wide")
st.markdown("<style>.main { background-color: #0b1016; color: #ffffff; }</style>", unsafe_allow_html=True)

def get_live_data():
    if os.path.exists("grid_state.json"):
        with open("grid_state.json", "r") as f: return json.load(f)
    return {"f": 60.0, "v": 115.0, "status": "SYNCING", "timestamp": time.time()}

data = get_live_data()
f_actual = data['f']
is_alert = f_actual < 59.95 or f_actual > 60.05

st.title("⚡ PRIMEnergeia S.A.S. - Sovereign Node VZA-400")
st.write(f"ENTIDAD LEGAL AUTORIZADA | STATUS: {'⚠️ ALERTA' if is_alert else '● NOMINAL'}")

m1, m2, m3 = st.columns(3)
m1.metric("FRECUENCIA", f"{f_actual:.3f} Hz", f"{round(f_actual-60, 4)}")
m2.metric("TENSIÓN", f"{data['v']} kV")
m3.metric("RESCATE ESTIMADO", "$2.54M USD")

t_sim = np.linspace(0, 0.05, 500)
shift = 2 * np.pi * f_actual * (data.get('timestamp', 0) % 1)
wave = np.sin(2 * np.pi * f_actual * t_sim + shift)
fig = go.Figure(go.Scatter(x=t_sim, y=wave, line=dict(color='#ff4b4b' if is_alert else '#00d1ff', width=4)))
fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0))
st.plotly_chart(fig, use_container_width=True)

st.divider()
if st.button("🔔 Trigger System Alert"):
    separator = "━━━━━━━━━━━━━━━━━━━━━━━━"
    status_str = "⚠️ ALERTA" if is_alert else "● NOMINAL"
    msg = f"🧠 DR. PRIME · PRIMEnergeia ALERT\n{separator}\nStatus: {status_str}\nFrequency: {f_actual:.3f} Hz\nVoltage: {data['v']} kV\n{separator}\nPRIMEnergeia S.A.S."
    success, info = send_telegram_notification(msg)
    if success:
        st.success("Notification sent to Telegram!")
    else:
        st.error(f"Failed to send: {info}")
    time.sleep(1)

time.sleep(0.2)
st.rerun()
