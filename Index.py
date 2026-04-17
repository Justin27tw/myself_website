import streamlit as st
import requests
import folium
import pandas as pd
from streamlit_folium import st_folium
import time

# 設定頁面與標題
st.set_page_config(page_title="港鐵即時動態地圖 Pro", layout="wide")

# --- 隱藏重整時的「變灰」特效 ---
st.markdown("""
    <style>
        .stApp, div[data-testid="stAppViewBlockContainer"] {
            opacity: 1 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 1. 定義精確車站座標對照表 (解決定位錯誤的核心) ---
# 這些座標是根據官方站點位置微調，確保標記在車站大樓上
STATION_COORDS = {
    "HOK": (22.2849, 114.1582), "KOW": (22.3040, 114.1610), "TSY": (22.3585, 114.1070),
    "AIR": (22.3153, 113.9364), "AWE": (22.3214, 113.9446), "CEN": (22.2820, 114.1584),
    "ADM": (22.2795, 114.1645), "TST": (22.2988, 114.1722), "JOR": (22.3049, 114.1717),
    "YMT": (22.3131, 114.1706), "MOK": (22.3193, 114.1694), "PRE": (22.3251, 114.1685),
    "HUH": (22.3028, 114.1813), "TAW": (22.3732, 114.1785), "SHT": (22.3817, 114.1887),
    "FOT": (22.3932, 114.1914), "UNI": (22.4132, 114.2104), "TAP": (22.4442, 114.1687),
    "FAN": (22.4925, 114.1394), "SHS": (22.5015, 114.1278), "LOW": (22.5293, 114.1121),
    "LMC": (22.5152, 114.0664), "DIS": (22.3155, 114.0450), "SUN": (22.3225, 114.0255),
    "TUC": (22.2978, 113.9395), "POA": (22.3235, 114.2580), "HAH": (22.3156, 114.2644),
    "TKO": (22.3073, 114.2595), "TIK": (22.3050, 114.2530), "YAT": (22.2988, 114.2386),
    "QUB": (22.2825, 114.2144), "NOP": (22.2913, 114.2006), "TUM": (22.3925, 113.9740),
    "SIH": (22.4116, 113.9818), "TIS": (22.4447, 114.0028), "LOP": (22.4475, 114.0233),
    "YUL": (22.4469, 114.0353), "KSR": (22.4338, 114.0655), "TWW": (22.3685, 114.1114),
    "MEF": (22.3364, 114.1391), "NAC": (22.3275, 114.1605), "AUS": (22.3045, 114.1664)
}

# --- 2. 資料載入 ---
@st.cache_data
def load_mtr_csv():
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    df = pd.read_csv(url)
    supported_lines = ["AEL", "TCL", "TML", "TKL", "EAL", "SIL", "TWL", "ISL", "KTL", "DRL"]
    df = df[df["Line Code"].isin(supported_lines)]
    return df.drop_duplicates(subset=["Line Code", "Station Code"])

def get_mtr_data(line, sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=TC"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

def format_html_popup(data, line, sta_code, sta_name):
    html = f"<div style='width:250px'><h4>{sta_name}</h4>"
    if not data:
        return html + "<p style='color:red'>暫無班次資料</p></div>"
    if data.get("status") == 0:
        return html + f"<p style='color:orange'>⚠️ {data.get('message')}</p></div>"
    
    schedule = data.get("data", {}).get(f"{line}-{sta_code}", {})
    for direction in ["UP", "DOWN"]:
        trains = schedule.get(direction, [])
        if trains:
            dir_label = "往港島/市區方向" if direction == "DOWN" else "往新界/離島方向"
            html += f"<b>{dir_label}:</b><table style='width:100%; font-size:12px;'>"
            for t in trains:
                time_val = t.get('time', '').split(" ")[1][:5]
                html += f"<tr><td>{t.get('dest')}</td><td align='center'>P{t.get('plat')}</td><td>{time_val}</td></tr>"
            html += "</table><br>"
    return html + "</div>"

# --- 3. UI 介面 ---
st.title("🚇 港鐵即時到站系統 (修正版)")
stations_df = load_mtr_csv()
line_map = {
    "AEL": "機場快綫", "TCL": "東涌綫", "TML": "屯馬綫", "TKL": "將軍澳綫",
    "EAL": "東鐵綫", "SIL": "南港島綫", "TWL": "荃灣綫", "ISL": "港島綫",
    "KTL": "觀塘綫", "DRL": "迪士尼綫"
}

with st.sidebar:
    st.header("⚙️ 設定")
    sel_line = st.selectbox("選擇路線", list(line_map.keys()), format_func=lambda x: f"{x} {line_map[x]}")
    auto_refresh = st.checkbox("啟動自動更新 (10秒)", value=True)

# --- 4. 地圖渲染 ---
@st.fragment(run_every=10 if auto_refresh else None)
def render_map():
    line_data = stations_df[stations_df["Line Code"] == sel_line]
    st.info(f"路線：{line_map[sel_line]} | 🕒 最後更新：{time.strftime('%H:%M:%S')}")
    
    # 根據路線第一個站點定位地圖中心
    first_sta = line_data.iloc[0]["Station Code"]
    center = STATION_COORDS.get(first_sta, (22.3, 114.15))
    m = folium.Map(location=center, zoom_start=12)

    for _, row in line_data.iterrows():
        code = row["Station Code"]
        name = row["Chinese Name"]
        
        # 優先從 STATION_COORDS 獲取精確位置
        coords = STATION_COORDS.get(code)
        if coords:
            data = get_mtr_data(sel_line, code)
            popup_html = format_html_popup(data, sel_line, code, name)
            folium.Marker(
                location=coords,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=name,
                icon=folium.Icon(color="blue", icon="train", prefix="fa")
            ).add_to(m)
            
    st_folium(m, width=1000, height=600, returned_objects=[])

render_map()