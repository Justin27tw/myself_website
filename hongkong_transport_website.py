import streamlit as st
import requests
import folium
import pandas as pd
from streamlit_folium import st_folium
import time
from geopy.geocoders import Nominatim

st.set_page_config(page_title="港鐵全綫即時動態地圖", layout="wide")

# --- 1. 讀取並整理港鐵官方 CSV 資料 ---
@st.cache_data
def load_mtr_csv():
    # 直接從開放數據 URL 讀取 CSV
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    df = pd.read_csv(url)
    
    # 根據 API 規格書，過濾出目前支援即時動態的路線
    supported_lines = ["AEL", "TCL", "TML", "TKL", "EAL", "SIL", "TWL", "ISL", "KTL", "DRL"]
    df = df[df["Line Code"].isin(supported_lines)]
    
    # 移除重複的車站 (因為 CSV 分上下行 Direction 會重複列出同一個車站)
    stations_df = df.drop_duplicates(subset=["Line Code", "Station Code"]).copy()
    return stations_df

# --- 2. 自動轉換車站名稱為經緯度 (Geocoding) ---
@st.cache_data
def get_coordinates(station_name_en):
    geolocator = Nominatim(user_agent="mtr_map_app")
    try:
        # 加上 "MTR Station, Hong Kong" 提高精準度
        query = f"{station_name_en} MTR Station, Hong Kong"
        location = geolocator.geocode(query, timeout=5)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    # 若搜尋不到，給予一個預設座標 (維多利亞港附近)
    return 22.2988, 114.1722

# --- 3. 獲取 API 即時班次 ---
def get_mtr_schedule(line, sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=TC"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # 在 API 資料字典中，status 為 1 代表正常
            if data.get("status") == 1:
                return data["data"].get(f"{line}-{sta}", {})
    except:
        pass
    return None

def format_schedule(schedule_data):
    if not schedule_data:
        return "目前無資料或發生錯誤"
    
    info = ""
    for direction in ["UP", "DOWN"]:
        if direction in schedule_data:
            dir_name = "上行" if direction == "UP" else "下行"
            info += f"<b>【{dir_name}】</b><br>"
            
            for train in schedule_data[direction]:
                dest = train.get('dest', '未知')
                plat = train.get('plat', '未知')
                # 擷取時間字串的最後 HH:mm:ss 部分
                time_str = train.get('time', '').split(" ")[-1]
                info += f"開往: {dest} | 月台: {plat} | 預計時間: {time_str}<br>"
            info += "<br>"
    return info if info else "目前無列車資訊"

# --- UI 介面設計 ---
st.title("🚇 港鐵全綫即時動態地圖")

# 讀取 CSV 站點資料
stations_df = load_mtr_csv()

# 路線中英文對照表 (用於側邊欄顯示)
line_dict = {
    "AEL": "機場快綫", "TCL": "東涌綫", "TML": "屯馬綫", "TKL": "將軍澳綫",
    "EAL": "東鐵綫", "SIL": "南港島綫", "TWL": "荃灣綫", "ISL": "港島綫",
    "KTL": "觀塘綫", "DRL": "迪士尼綫"
}

# 建立側邊欄讓使用者選擇路線
st.sidebar.header("🗺️ 地圖設定")
selected_line = st.sidebar.selectbox(
    "請選擇要查看的港鐵路線：", 
    stations_df["Line Code"].unique(),
    format_func=lambda x: f"{x} - {line_dict.get(x, x)}"
)

# 過濾出所選路線的所有車站
line_stations = stations_df[stations_df["Line Code"] == selected_line]

st.write(f"最後更新時間: **{time.strftime('%Y-%m-%d %H:%M:%S')}** (每 10 秒自動更新本頁面)")

# --- 建立地圖 ---
if not line_stations.empty:
    # 依照該路線的第一個車站作為地圖的初始中心點
    first_sta_en = line_stations.iloc[0]["English Name"]
    center_lat, center_lon = get_coordinates(first_sta_en)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # 將該路線的每個車站加入地圖
    for index, row in line_stations.iterrows():
        sta_code = row["Station Code"]
        sta_name_zh = row["Chinese Name"]
        sta_name_en = row["English Name"]
        
        # 1. 取得座標
        lat, lon = get_coordinates(sta_name_en)
        # 2. 取得該站即時班次
        schedule = get_mtr_schedule(selected_line, sta_code)
        
        # 3. 組合地圖彈出視窗 (Popup) 內容
        popup_content = f"<h4>{sta_name_zh} ({sta_code})</h4>"
        popup_content += format_schedule(schedule)
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"點擊查看 {sta_name_zh} 班次",
            icon=folium.Icon(color="blue", icon="train", prefix='fa')
        ).add_to(m)

    # 顯示地圖
    st_folium(m, width=900, height=500)

# 讓 Streamlit 每 10 秒自動重新執行此腳本 (模擬動態更新)
time.sleep(10)
st.rerun()