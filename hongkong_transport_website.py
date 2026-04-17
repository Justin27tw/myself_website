import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import time

# 設定頁面自動每 10 秒重整一次 (符合港鐵 API 更新頻率)
st.set_page_config(page_title="港鐵即時動態地圖", layout="wide")

# 1. 建立車站經緯度與代碼字典 (以機場快綫 AEL 為例)
STATIONS = {
    "HOK": {"name": "香港 (Hong Kong)", "lat": 22.2849, "lon": 114.1582},
    "KOW": {"name": "九龍 (Kowloon)", "lat": 22.3049, "lon": 114.1615},
    "TSY": {"name": "青衣 (Tsing Yi)", "lat": 22.3585, "lon": 114.1070},
    "AIR": {"name": "機場 (Airport)", "lat": 22.3153, "lon": 113.9364},
    "AWE": {"name": "博覽館 (AsiaWorld-Expo)", "lat": 22.3214, "lon": 113.9446}
}

LINE_CODE = "AEL"

# 2. 獲取港鐵 API 資料的函數
def get_mtr_data(line, sta):
    # 使用 API 規格書中的 URL，並將語言設定為繁體中文 (TC)
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=TC"
    try:
        response = requests.get(url)
        data = response.json()
        
        # 檢查 API 狀態碼，1 代表成功
        if data.get("status") == 1:
            return data["data"].get(f"{line}-{sta}", {})
        else:
            return None
    except Exception as e:
        return None

# 3. 解析到站時間的函數
def format_train_schedule(schedule_data):
    if not schedule_data:
        return "目前無資料或發生錯誤"
    
    info = ""
    # 解析 UP (上行) 與 DOWN (下行) 方向的列車
    for direction in ["UP", "DOWN"]:
        if direction in schedule_data:
            dir_name = "上行 (往博覽館/機場)" if direction == "UP" else "下行 (往香港)"
            info += f"<b>【{dir_name}】</b><br>"
            
            # 取出未來幾班列車的資訊
            trains = schedule_data[direction]
            for train in trains:
                dest = train.get('dest', '未知')
                plat = train.get('plat', '未知')
                time_str = train.get('time', '').split(" ")[-1] # 只取時間部分 HH:mm:ss
                info += f"開往: {dest} | 月台: {plat} | 預計時間: {time_str}<br>"
            info += "<br>"
    return info if info else "目前無列車資訊"

# 4. 建立 Streamlit 介面與地圖
st.title("🚇 港鐵 (MTR) 即時動態地圖 - 機場快綫")
st.write(f"最後更新時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 初始化 Folium 地圖，中心點設定在青衣站附近
m = folium.Map(location=[22.315, 114.107], zoom_start=12)

# 逐一向 API 查詢各站資料，並標記在地圖上
for sta_code, sta_info in STATIONS.items():
    # 呼叫 API
    schedule = get_mtr_data(LINE_CODE, sta_code)
    
    # 將 JSON 資料格式化為 HTML 文字
    popup_content = f"<h4>{sta_info['name']}</h4>"
    popup_content += format_train_schedule(schedule)
    
    # 建立地圖標記 (Marker)
    folium.Marker(
        location=[sta_info["lat"], sta_info["lon"]],
        popup=folium.Popup(popup_content, max_width=300),
        tooltip=f"點擊查看 {sta_info['name']} 即時班次",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

# 在網頁上顯示地圖
st_folium(m, width=800, height=500)

# 5. 設定自動重新整理 (等待 10 秒後重跑整個腳本)
time.sleep(10)
st.rerun()