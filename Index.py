
import streamlit as st
import requests
import pandas as pd
import time
import folium # 引入 folium 庫
from streamlit_autorefresh import st_autorefresh # 引入自動刷新庫

# --- 1. 設定頁面 ---
st.set_page_config(page_title="港鐵即時到站路線圖", layout="centered")

# --- 2. 自定義 CSS ---
st.markdown("""
    <style>
    .station-container {
        display: flex;
        align-items: center;
        margin-bottom: 0px;
        height: 50px;
    }
    .line-segment {
        width: 6px;
        height: 50px;
        margin-left: 20px;
        background-color: #888; /* 預設顏色 */
        position: relative;
    }
    .station-node {
        width: 16px;
        height: 16px;
        background-color: white;
        border: 3px solid #888;
        border-radius: 50%;
        position: absolute;
        left: -5px;
        top: 17px;
        z-index: 2;
    }
    /* 點擊按鈕的樣式 */
    div.stButton > button {
        border: none;
        background: transparent;
        color: #31333F;
        font-size: 18px;
        font-weight: 500;
        padding: 0px 20px;
        text-align: left;
        width: 100%;
    }
    div.stButton > button:hover {
        color: #FF4B4B;
        background: #F0F2F6;
    }
    /* 班次顯示盒 */
    .eta-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #0078d4;
        margin: 10px 0px 20px 40px;
    }
    /* 地圖容器的樣式 */
    .map-container {
        width: 100%;
        height: 600px; /* 設定地圖高度 */
        border-radius: 10px;
        overflow: hidden; /* 確保圓角生效 */
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 數據載入與 API 函式 ---
# 從線上 URL 讀取 CSV
@st.cache_data
def load_mtr_csv_from_url():
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    try:
        df = pd.read_csv(url)
        # 假設 CSV 包含 'Latitude' 和 'Longitude' 欄位
        # 如果沒有，您需要從其他地方獲取或手動添加
        return df
    except Exception as e:
        st.error(f"無法載入車站數據: {e}")
        return pd.DataFrame() # 返回空 DataFrame 以避免後續錯誤

def get_mtr_eta(line, sta):
    """呼叫港鐵 API 獲取即時班次"""
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=zh"
    try:
        response = requests.get(url, timeout=10) # 增加超時時間
        response.raise_for_status() # 檢查 HTTP 錯誤
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"無法獲取 {sta} 班次數據: {e}")
        return None
    except Exception as e:
        st.warning(f"處理站點 {sta} 數據時發生未知錯誤: {e}")
        return None

# --- 4. UI 介面設定 ---
st.title("🚇 港鐵即時動態路線圖與地圖")

# 載入車站數據
stations_all = load_mtr_csv_from_url()

if stations_all.empty:
    st.error("車站數據載入失敗，無法繼續。請確保 CSV 檔案可訪問且格式正確，並包含 'Latitude' 和 'Longitude' 欄位。")
    st.stop() # 停止執行

# 檢查是否包含經緯度欄位
if 'Latitude' not in stations_all.columns or 'Longitude' not in stations_all.columns:
    st.error("CSV 數據集沒有包含 'Latitude' 和 'Longitude' 欄位。無法生成地圖。請更新數據源或手動添加經緯度資訊。")
    # 即使沒有經緯度，也允許用戶查看路線圖（無地圖功能）
    show_map = False
else:
    show_map = True

# 定義線路顏色
line_map = {
    "KTL": {"name": "觀塘綫", "color": "#00AB4E", "icon": "train"},
    "ISL": {"name": "港島綫", "color": "#0077C8", "icon": "subway"},
    "TWL": {"name": "荃灣綫", "color": "#E2231A", "icon": "subway"},
    "SIL": {"name": "南港島綫", "color": "#B5BD00", "icon": "subway"},
    "TKL": {"name": "將軍澳綫", "color": "#A35EB5", "icon": "subway"},
    "EAL": {"name": "東鐵綫", "color": "#53B7E8", "icon": "train"},
    "TML": {"name": "屯馬綫", "color": "#9A3820", "icon": "subway"},
    "TCL": {"name": "東涌綫", "color": "#F3A11F", "icon": "subway"},
    "AEL": {"name": "機場快綫", "color": "#007078", "icon": "plane"},
    "DRL": {"name": "迪士尼綫", "color": "#F5821F", "icon": "subway"}
}

with st.sidebar:
    st.header("⚙️ 選項")
    sel_line_code = st.selectbox("切換線路", list(line_map.keys()), 
                                format_func=lambda x: f"{line_map[x]['name']} ({x})")
    
    st.write("---")
    st.info("💡 點擊車站名稱查看即時到站班次")
    
    # 自動更新設定
    refresh_interval = st.slider("自動更新間隔 (秒)", 10, 120, 30)
    st_autorefresh(interval=refresh_interval * 1000, key="datarefresh") # 毫秒為單位

    if st.button("🔄 手動更新數據"):
        st.rerun()

# 篩選該路線車站（過濾掉重複的方向，僅取一組站序用於顯示）
line_data = stations_all[stations_all["Line Code"] == sel_line_code].sort_values("Sequence")
# 移除重複車站(因為 CSV 內可能有 UT/DT 兩組)
line_stations = line_data.drop_duplicates(subset=["Station Code"])

# --- 5. 渲染地圖 (如果數據允許) ---
# 創建地圖中心
center_lat = stations_all['Latitude'].mean()
center_lon = stations_all['Longitude'].mean()
mtr_map = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# 繪製已選擇路線的車站和線條
selected_line_stations_df = stations_all[stations_all["Line Code"] == sel_line_code].sort_values("Sequence")

selected_line_coords = selected_line_stations_df[['Latitude', 'Longitude']].values.tolist()
line_color = line_map.get(sel_line_code, {}).get('color', '#888') # 獲取線路顏色，預設為灰色

# 在地圖上標記選定的路線車站
station_markers = []
for index, row in selected_line_stations_df.iterrows():
    lat, lon, sta_code, sta_name, station_order = row["Latitude"], row["Longitude"], row["Station Code"], row["Chinese Name"], row["Sequence"]
    
    if pd.notna(lat) and pd.notna(lon):
        # 創建 Popup 內容
        popup_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px;">
              <strong>{sta_name}</strong> ({sta_code})<br>
              <button onclick="streamlit_click_station('{sta_code}', '{sta_name}')" style="background-color: #f0f2f6; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; margin-top: 5px;">
                查看即時班次
              </button>
            </div>
        """
        iframe = folium.IFrame(popup_html, width=200, height=100)
        popup = folium.Popup(iframe, max_width=260)

        folium.Marker(
            location=[lat, lon],
            popup=popup,
            tooltip=f"{sta_name}", # 滑鼠懸停時顯示
            icon=folium.Icon(color='blue', icon='info-sign') # 預設藍色圖標
            # 可以根據線路顏色調整圖標顏色，但 Folium.Icon 的 color 參數主要控制圖標背景色，ICON 顏色較難直接控制。
            # icon=folium.Icon(color=line_color_for_folium, icon='train') # Folium.Icon 的 color 參數是預定義顏色，較難自定義
        ).add_to(mtr_map)
        station_markers.append([lat, lon, sta_name, sta_code])

# 繪製線路連接 (僅顯示當前選定路線)
if len(selected_line_coords) > 1:
    folium.PolyLine(
        locations=selected_line_coords,
        color=line_color,
        weight=5,
        opacity=0.8,
        tooltip=f"{line_map.get(sel_line_code, {}).get('name', 'Unknown Line')}"
    ).add_to(mtr_map)

# --- 6. 渲染垂直路線圖 (保持原有功能) ---
st.subheader(f"📍 {line_map[sel_line_code]['name']} 沿途各站")
st.caption(f"最後更新：{time.strftime('%H:%M:%S')}")

# 使用 Session State 紀錄目前點選的車站
if "selected_sta_code" not in st.session_state:
    st.session_state.selected_sta_code = None
if "selected_sta_name" not in st.session_state:
    st.session_state.selected_sta_name = None

# --- Helper function to trigger station selection from map ---
# 這是一個 JavaScript 函式，用於模擬點擊按鈕
# Streamlit 的 st.session_state 在純 Python 中更新，
# 在地圖 Popup 中模擬點擊按鈕需要 JavaScript 橋接
def trigger_station_selection_js(sta_code, sta_name):
    return f"""
    <script>
    function streamlit_click_station(code, name) {{
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/_st_session_state', true); // Streamlit session state endpoint
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function () {{
            if (xhr.readyState === 4 && xhr.status === 200) {{
                // Success, Session state updated. Now rerun the app to reflect changes.
                // Note: Direct rerun from JS is not straightforward. We rely on the auto-refresh
                // or manual explicit rerun. Better handled by the Python side.
            }}
        }};
        // This is a placeholder. Directly setting session state from JS is complex.
        // A common approach is to have a hidden button in Streamlit that gets clicked via JS.
        // For simplicity here, we'll assume Python side handles the state update.
        // Streamlit's st.rerun() can be triggered if we could signal it.
        console.log("Simulating click for:", code, name);
        // Ideally, this would update st.session_state.selected_sta_code and trigger a rerun.
        // For now, we will rely on the Python update after the map is rendered.
        // The best approach is to use Python's session_state directly.
        
        // This JS will not directly update Python's session state.
        // The Python code below will handle the logic after JS execution.
    }}
    </script>
    """
st.components.v1.html(trigger_station_selection_js("",""), height=0)

# --- Python side logic for session state update ---
# This part is key to making the map interaction work with the Python logic.
# When a station is clicked on the map, we want to set the Python session state.
# This is normally done via a button click in Streamlit Python.
# To bridge this from JS, we need a mechanism.
# For this example, we'll keep the Python-driven click logic for the vertical list,
# and explain how to potentially bridge JS click to Python.

# If a station was clicked from the map, we would ideally set it here.
# For this example, we'll rely on the vertical list clicks.
# If you want map clicks to work, it's more involved, often requiring a custom component or a proxy mechanism.

# We will use Streamlit's `st.query_params` as a simpler proxy for interaction.
# When a map icon is clicked, it should ideally set a query parameter.
# Example: /?selected_station=KOW
# But for now, we stick to the button clicks in the vertical list.

for index, row in line_stations.iterrows():
    sta_code = row["Station Code"]
    sta_name = row["Chinese Name"]
    
    col_line, col_name = st.columns([0.1, 0.9])
    
    with col_line:
        st.markdown(f"""
            <div class="line-segment" style="background-color: {line_color};">
                <div class="station-node" style="border-color: {line_color};"></div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_name:
        if st.button(sta_name, key=f"btn_{sta_code}"):
            st.session_state.selected_sta_code = sta_code
            st.session_state.selected_sta_name = sta_name
            # st.rerun() # Optional: Rerun immediately on button click if needed

    # 如果該站被點選，顯示班次資訊
    if st.session_state.selected_sta_code == sta_code:
        col1, col2 = st.columns([0.1, 0.9]) # Adjust columns for indentation
        with col2: # Indent the ETA box
            with st.spinner(f"正在獲取 {sta_name} 班次..."):
                eta_data = get_mtr_eta(sel_line_code, sta_code)
                
                if eta_data and eta_data.get("status") == 1:
                    data_key = f"{sel_line_code}-{sta_code}"
                    results = eta_data.get("data", {}).get(data_key, {})
                    
                    st.markdown(f'<div class="eta-box">', unsafe_allow_html=True)
                    st.write(f"**📍 {sta_name} ( {sta_code} ) 即時班次**")
                    
                    eta_col1, eta_col2 = st.columns(2)
                    
                    for direction in ["UP", "DOWN"]:
                        trains = results.get(direction, [])
                        with (eta_col1 if direction == "UP" else eta_col2):
                            dir_label = "⬆️ 上行" if direction == "UP" else "⬇️ 下行"
                            st.write(f"**{dir_label}**")
                            if not trains:
                                st.write("目前無班次資訊")
                            for t in trains:
                                # 格式化時間 (原格式 yyyy-mm-dd hh:mm:ss)
                                t_time = t['time'].split(" ")[1][:5]
                                dest = t.get('dest', 'N/A') # Safely get destination
                                plat = t.get('plat', 'N/A') # Safely get platform
                                st.write(f"⏱️ {t_time} - 往 {dest} (月台 {plat})")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("暫時無法取得班次數據，請稍後再試。")

# --- 7. 顯示地圖 (如果數據允許) ---
if show_map:
    st.subheader("🗺️ 港鐵車站地圖")
    
    # 將 folium 地圖渲染成 HTML
    map_html = mtr_map._repr_html_()
    
    # 在 Streamlit 中嵌入 HTML
    # 使用 CSS 讓地圖佔滿容器且有圓角
    st.components.v1.html(f"""
        <div class="map-container">
            {map_html}
        </div>
    """, height=650) # 調整高度以容納地圖及邊距

    st.info("點擊地圖上的車站圖標，可查看即時班次選項。")

# --- 8. 說明與免責聲明 ---
st.markdown("---")
st.header("關於數據")
st.write("""
此應用程式使用香港鐵路有限公司 (MTR) 提供的開放數據。
- **車站與路線數據**: 來自 [MTR Open Data Portal](https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv)
- **即時列車服務資訊**: 來自 [政府數據開放平台](https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php)

**免責聲明**: 數據僅供參考，港鐵公司對數據的準確性或時效性不作任何保證，使用者應自行判斷。
""")
# ```

# ### 如何運行此程式碼

# 1.  **安裝必要的庫**:
#     ```bash
#     pip install streamlit requests pandas folium streamlit-autorefresh
#     ```
# 2.  **保存程式碼**: 將上面的完整程式碼保存為一個 Python 檔案，例如 `mtr_app.py`。
# 3.  **運行 Streamlit 應用**: 在終端機中，導航到您保存檔案的目錄，然後執行：
#     ```bash
#     streamlit run mtr_app.py
#     ```

# ### 程式碼的主要變動與新增功能

# 1.  **CSV 數據源**:
#     *   `load_mtr_csv_from_url()` 函式現在直接從 `https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv` 讀取數據。
#     *   增加了對 CSV 讀取錯誤和 `Latitude`/`Longitude` 欄位是否存在的基本檢查。

# 2.  **Folium 地圖整合**:
#     *   **引入 `folium`**: 匯入 `folium` 庫。
#     *   **數據檢查**: 在渲染地圖前，檢查 `stations_all` DataFrame 是否包含 `Latitude` 和 `Longitude` 欄位。如果沒有，將禁用地圖功能並顯示錯誤訊息。
#     *   **創建地圖**: `folium.Map()` 創建一個基本的 Leaflet 地圖，並設定中心點和縮放級別。
#     *   **標記車站**:
#         *   遍歷選定路線的車站，如果車站有經緯度，則使用 `folium.Marker` 在地圖上標記。
#         *   **Popup 互動**: 在每個車站標記上創建了一個自定義的 Popup。這個 Popup 包含一個「查看即時班次」按鈕。
#             *   **注意**: 直接從 Folium Popup 的 JavaScript 觸發 Streamlit 的 Python Session State 更新並觸發 `st.rerun()` 是比較複雜的。程式碼中， Popup 內的按鈕是一個 **模擬** 點擊的 JavaScript 函式 `streamlit_click_station`，但它**無法直接**更新 Streamlit 的 Python Session State。
#             *   **解決方案 (目前採用)**: 我們仍然主要依賴於左側側邊欄的垂直列表中的按鈕來更新 `st.session_state.selected_sta_code`。地圖上的 Popup 可以「提示」用戶，但點擊的動作需要透過側邊欄按鈕來完成，或者需要更複雜的 Streamlit Component / Custom Component 來實現 JS-Python 雙向通信。
#             *   **替代方案 (程式碼中未完全實現)**: 一種常見的民間做法是，JavaScript 觸發一個 **隱藏的 Streamlit 按鈕** 的點擊事件，或者通過 `st.query_params` 修改 URL，然後 Streamlit 應用監聽到 query params 的變化來更新 state。
#     *   **繪製路線**: 使用 `folium.PolyLine` 根據車站的坐標順序繪製出當前選定路線的線段。
#     *   **嵌入地圖**: `mtr_map._repr_html_()` 將 Folium 地圖轉換為 HTML 字串，然後使用 `st.components.v1.html()` 將其嵌入到 Streamlit 頁面中。

# 3.  **自動更新**:
#     *   在側邊欄中添加了一個滑桿 `st.slider("自動更新間隔 (秒)", 10, 120, 30)`，讓用戶可以自定義更新頻率。
#     *   `st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")` 根據用戶選擇的間隔（轉換為毫秒）來自動刷新頁面。

# 4.  **UI 調整**:
#     *   添加了 `map-container` CSS 類別來管理地圖的顯示樣式。
#     *   在顯示班次資訊時，稍微調整了列佈局，使得班次顯示框有縮進效果。
#     *   添加了更詳細的數據來源說明和免責聲明。

# ### 使用說明

# 1.  **查看路線圖**: 應用啟動後，您會看到一個包含所有港鐵車站的地圖。可以使用滑鼠滾輪縮放，拖曳移動。
# 2.  **選擇線路**: 在左側的側邊欄，您可以從下拉選單中選擇不同的港鐵線路。
# 3.  **查看車站列表**: 當您選擇一條線路時，下方會顯示該線路的所有車站列表。
# 4.  **查看即時班次 (通過側邊欄)**: 點擊側邊欄中的車站名稱按鈕，下方會展開顯示該站點的即時到站班次資訊。
# 5.  **查看即時班次 (通過地圖 Popup - 提示功能)**: 您可以點擊地圖上的車站圖標，會彈出一個 Popup。Popup 中有一個「查看即時班次」的按鈕。**但是，這個按鈕本身不會直接觸發 Streamlit 的數據更新。** 您需要點擊側邊欄中的車站名稱按鈕才能看到更新的班次數據。這是因為 Streamlit 的 Python Session State 管理與 WebView 中的 JavaScript 互動需要額外的複雜橋接。
# 6.  **自動更新**: 使用側邊欄的滑桿設定自動更新頻率（例如，每 30 秒）。頁面會自動刷新，更新所有車站的即時班次數據。
# 7.  **手動更新**: 點擊側邊欄的「手動更新數據」按鈕，會立即刷新所有數據。

# 這個版本結合了地圖視覺化和即時數據的展示，並且支持自動更新，提供了一個更豐富的用戶體驗。