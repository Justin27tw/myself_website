import streamlit as st
import requests
import folium
import pandas as pd
from streamlit_folium import st_folium
import time
from geopy.geocoders import Nominatim

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

# --- 1. 資料載入與快取 ---
@st.cache_data
def load_mtr_csv():
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    df = pd.read_csv(url)
    supported_lines = ["AEL", "TCL", "TML", "TKL", "EAL", "SIL", "TWL", "ISL", "KTL", "DRL"]
    df = df[df["Line Code"].isin(supported_lines)]
    return df.drop_duplicates(subset=["Line Code", "Station Code"])

@st.cache_data
def get_coords(station_en):
    geolocator = Nominatim(user_agent="mtr_app_v2")
    try:
        loc = geolocator.geocode(f"{station_en} MTR Station, Hong Kong", timeout=5)
        return (loc.latitude, loc.longitude) if loc else (22.2988, 114.1722)
    except:
        return 22.2988, 114.1722

# --- 2. API 數據獲取與解析 ---
def get_mtr_data(line, sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=TC"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

# 修正：這裡多加了 sta_code 參數
def format_html_popup(data, line, sta_code, sta_name):
    html = f"<div style='width:250px'><h4>{sta_name}</h4>"
    
    if not data:
        return html + "<p style='color:red'>無法取得即時數據</p></div>"
    
    if data.get("status") == 0:
        msg = data.get("message", "車站服務受阻")
        return html + f"<p style='color:orange'>⚠️ {msg}</p></div>"
    
    delay_status = "✅ 運作正常" if data.get("isdelay") == "N" else "⚠️ 列車延誤"
    html += f"<p><small>{delay_status}</small></p>"

    # 修正：使用 sta_code 來抓取對應的字典資料
    schedule = data.get("data", {}).get(f"{line}-{sta_code}", {})
    
    for direction in ["UP", "DOWN"]:
        trains = schedule.get(direction, [])
        if trains:
            dir_label = "往港島/市區方向" if direction == "DOWN" else "往新界/離島方向"
            html += f"<b>{dir_label}:</b><table style='width:100%; border-collapse: collapse; font-size:12px;'>"
            html += "<tr><th>目的地</th><th>月台</th><th>時間</th></tr>"
            
            for t in trains:
                dest = t.get('dest')
                plat = t.get('plat')
                time_val = t.get('time', '').split(" ")[1][:5]
                route_info = " (經馬場)" if t.get('route') == "RAC" else ""
                type_info = " (抵達)" if t.get('timetype') == "A" else ""
                html += f"<tr><td>{dest}{route_info}</td><td align='center'>{plat}</td><td>{time_val}{type_info}</td></tr>"
            html += "</table><br>"
            
    if "UP" not in schedule and "DOWN" not in schedule:
        html += "<p>目前沒有即時班次資訊</p>"
        
    return html + "</div>"

# --- 3. UI 佈局 ---
st.title("🚇 港鐵即時到站系統")
stations_df = load_mtr_csv()

line_map = {
    "AEL": "機場快綫", "TCL": "東涌綫", "TML": "屯馬綫", "TKL": "將軍澳綫",
    "EAL": "東鐵綫", "SIL": "南港島綫", "TWL": "荃灣綫", "ISL": "港島綫",
    "KTL": "觀塘綫", "DRL": "迪士尼綫"
}

with st.sidebar:
    st.header("⚙️ 設定")
    sel_line = st.selectbox("選擇路線", list(line_map.keys()), format_func=lambda x: f"{x} {line_map[x]}")
    auto_refresh = st.checkbox("啟動自動更新 (每 10 秒)", value=True)

line_data = stations_df[stations_df["Line Code"] == sel_line]

# --- 4. 地圖渲染 ---
@st.fragment(run_every=10 if auto_refresh else None)
def render_dynamic_map():
    st.info(f"正在顯示：{line_map[sel_line]} | 🕒 最後更新時間：{time.strftime('%H:%M:%S')}")
    
    if not line_data.empty:
        mid_idx = len(line_data) // 2
        center = get_coords(line_data.iloc[mid_idx]["English Name"])
        m = folium.Map(location=center, zoom_start=12)

        for _, row in line_data.iterrows():
            sta_code = row["Station Code"]
            sta_name = row["Chinese Name"]
            coords = get_coords(row["English Name"])
            
            api_resp = get_mtr_data(sel_line, sta_code)
            
            # 修正：把 sta_code 一併傳進去
            popup_html = format_html_popup(api_resp, sel_line, sta_code, sta_name)
            
            folium.Marker(
                location=coords,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=sta_name,
                icon=folium.Icon(color="blue", icon="train", prefix="fa")
            ).add_to(m)

        st_folium(m, width=1000, height=600, returned_objects=[])

render_dynamic_map()