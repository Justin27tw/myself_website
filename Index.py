import streamlit as st
import requests
import pandas as pd
import time

# 設定頁面
st.set_page_config(page_title="港鐵即時到站路線圖", layout="centered")

# --- 1. 自定義 CSS：打造垂直路線圖視覺 ---
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
    </style>
""", unsafe_allow_html=True)

# --- 2. 數據載入與 API 函式 ---
@st.cache_data
def load_mtr_csv():
    # 讀取車站資料
    df = pd.read_csv("mtr_lines_and_stations.csv")
    return df

def get_mtr_eta(line, sta):
    """呼叫港鐵 API 獲取即時班次"""
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=zh"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

# --- 3. UI 介面設定 ---
st.title("🚇 港鐵動態路線圖")

stations_all = load_mtr_csv()
line_map = {
    "KTL": {"name": "觀塘綫", "color": "#00AB4E"},
    "ISL": {"name": "港島綫", "color": "#0077C8"},
    "TWL": {"name": "荃灣綫", "color": "#E2231A"},
    "SIL": {"name": "南港島綫", "color": "#B5BD00"},
    "TKL": {"name": "將軍澳綫", "color": "#A35EB5"},
    "EAL": {"name": "東鐵綫", "color": "#53B7E8"},
    "TML": {"name": "屯馬綫", "color": "#9A3820"},
    "TCL": {"name": "東涌綫", "color": "#F3A11F"},
    "AEL": {"name": "機場快綫", "color": "#007078"},
    "DRL": {"name": "迪士尼綫", "color": "#F5821F"}
}

with st.sidebar:
    st.header("⚙️ 選項")
    sel_line_code = st.selectbox("切換線路", list(line_map.keys()), 
                                format_func=lambda x: f"{line_map[x]['name']} ({x})")
    
    st.write("---")
    st.info("💡 點擊車站名稱查看即時到站班次")
    if st.button("🔄 手動更新數據"):
        st.rerun()

# 篩選該路線車站（過濾掉重複的方向，僅取一組站序用於顯示）
line_data = stations_all[stations_all["Line Code"] == sel_line_code].sort_values("Sequence")
# 移除重複車站(因為 CSV 內可能有 UT/DT 兩組)
line_stations = line_data.drop_duplicates(subset=["Station Code"])

# --- 4. 渲染垂直路線圖 ---
line_color = line_map[sel_line_code]['color']
st.subheader(f"{line_map[sel_line_code]['name']} 沿途各站")
st.caption(f"最後更新：{time.strftime('%H:%M:%S')}")

# 使用 Session State 紀錄目前點選的車站
if "selected_sta" not in st.session_state:
    st.session_state.selected_sta = None

for index, row in line_stations.iterrows():
    sta_code = row["Station Code"]
    sta_name = row["Chinese Name"]
    
    # 建立垂直線段與節點
    col_line, col_name = st.columns([0.1, 0.9])
    
    with col_line:
        # 動態產生該線路顏色的 HTML
        st.markdown(f"""
            <div class="line-segment" style="background-color: {line_color};">
                <div class="station-node" style="border-color: {line_color};"></div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_name:
        # 使用按鈕當作車站點擊介面
        if st.button(sta_name, key=f"btn_{sta_code}"):
            st.session_state.selected_sta = sta_code
            st.session_state.selected_sta_name = sta_name
            
    # 如果該站被點選，顯示班次資訊
    if st.session_state.selected_sta == sta_code:
        with st.spinner(f"正在獲取 {sta_name} 班次..."):
            eta_data = get_mtr_eta(sel_line_code, sta_code)
            
            if eta_data and eta_data.get("status") == 1:
                data_key = f"{sel_line_code}-{sta_code}"
                results = eta_data.get("data", {}).get(data_key, {})
                
                # 準備顯示班次
                st.markdown(f'<div class="eta-box">', unsafe_allow_html=True)
                st.write(f"**📍 {sta_name} ( {sta_code} ) 即時班次**")
                
                col1, col2 = st.columns(2)
                
                for direction in ["UP", "DOWN"]:
                    trains = results.get(direction, [])
                    with (col1 if direction == "UP" else col2):
                        dir_label = "⬆️ 上行" if direction == "UP" else "⬇️ 下行"
                        st.write(f"**{dir_label}**")
                        if not trains:
                            st.write("目前無班次資訊")
                        for t in trains:
                            # 格式化時間 (原格式 yyyy-mm-dd hh:mm:ss)
                            t_time = t['time'].split(" ")[1][:5]
                            dest = t['dest']
                            # 轉換目的地代碼為中文 (可視需求進一步對應 CSV)
                            st.write(f"⏱️ {t_time} - 往 {dest} (月台 {t['plat']})")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("暫時無法取得班次數據，請稍後再試。")

# --- 5. 自動重整 (選配) ---
# 如果需要每分鐘自動更新，可以加入以下程式碼：
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30000, key="datarefresh") # 每30秒重整一次