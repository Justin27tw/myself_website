import streamlit as st
import requests
import pandas as pd
import time

# 設定頁面
st.set_page_config(page_title="港鐵即時到站路線圖", layout="centered")

# --- 1. 注入自定義 CSS：美化垂直線路排版 ---
st.markdown("""
    <style>
    /* 隱藏重整時的變灰效果 */
    .stApp { opacity: 1 !important; }
    
    /* 垂直線路容器 */
    .route-container {
        padding-left: 40px;
        border-left: 6px solid #888888; /* 預設灰線 */
        margin-left: 20px;
        position: relative;
    }
    
    /* 路線特定顏色 (根據港鐵官方顏色) */
    .line-AEL { border-left-color: #007078; }
    .line-TCL { border-left-color: #F3A11F; }
    .line-TML { border-left-color: #9A3820; }
    .line-TKL { border-left-color: #A35EB5; }
    .line-EAL { border-left-color: #53B7E8; }
    .line-SIL { border-left-color: #B5BD00; }
    .line-TWL { border-left-color: #E2231A; }
    .line-ISL { border-left-color: #007AB7; }
    .line-KTL { border-left-color: #00AF41; }
    .line-DRL { border-left-color: #F58282; }

    /* 車站圓點 */
    .station-dot {
        position: absolute;
        left: -13px;
        width: 20px;
        height: 20px;
        background-color: white;
        border: 4px solid #333;
        border-radius: 50%;
        z-index: 10;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心功能函數 ---
@st.cache_data
def load_mtr_csv():
    # 讀取車站資料 [cite: 212]
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    df = pd.read_csv(url)
    supported_lines = ["AEL", "TCL", "TML", "TKL", "EAL", "SIL", "TWL", "ISL", "KTL", "DRL"]
    df = df[df["Line Code"].isin(supported_lines)]
    # 只取單一方向來排列車站，避免重複 [cite: 212]
    return df[df["Direction"] == "UP"].sort_values(by="Sequence")

def get_mtr_data(line, sta):
    # 呼叫港鐵 API [cite: 22, 25]
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=TC"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

def display_timetable(data, line, sta_code):
    # 格式化顯示時刻表 
    if not data or data.get("status") == 0:
        st.warning(data.get("message", "暫無即時資訊") if data else "連線失敗")
        return

    schedule = data.get("data", {}).get(f"{line}-{sta_code}", {})
    
    # 檢查是否有延誤 [cite: 206]
    if data.get("isdelay") == "Y":
        st.error("⚠️ 列車服務延誤")

    cols = st.columns(2)
    for idx, direction in enumerate(["UP", "DOWN"]):
        with cols[idx]:
            dir_name = "往新界/博覽館" if direction == "UP" else "往市區/香港"
            st.write(f"**{dir_label_mapping(line, direction)}**")
            
            trains = schedule.get(direction, [])
            if not trains:
                st.write(" 無班次")
                continue
                
            for t in trains:
                # 取得時間並過濾日期部分 [cite: 209]
                time_val = t.get('time', '').split(" ")[1][:5]
                # 東鐵線特殊標記 [cite: 209]
                route_info = " (經馬場)" if t.get('route') == "RAC" else ""
                st.caption(f"🏁 {t.get('dest')}{route_info} | 📍 月台 {t.get('plat')} | 🕒 {time_val}")

def dir_label_mapping(line, direction):
    # 根據路線提供更精確的方向描述 
    mapping = {
        "AEL": {"UP": "往博覽館", "DOWN": "往香港"},
        "TCL": {"UP": "往東涌", "DOWN": "往香港"},
        "EAL": {"UP": "往羅湖/落馬洲", "DOWN": "往金鐘"},
        "TML": {"UP": "往烏溪沙", "DOWN": "往屯門"},
        "TKL": {"UP": "往寶琳/康城", "DOWN": "往北角"},
        "TWL": {"UP": "往荃灣", "DOWN": "往中環"},
        "ISL": {"UP": "往柴灣", "DOWN": "往堅尼地城"},
        "KTL": {"UP": "往調景嶺", "DOWN": "往黃埔"},
        "SIL": {"UP": "往海怡半島", "DOWN": "往金鐘"},
        "DRL": {"UP": "往迪士尼", "DOWN": "往欣澳"}
    }
    return mapping.get(line, {}).get(direction, direction)

# --- 3. UI 介面設計 ---
st.title("🚇 港鐵動態路線圖")

stations_all = load_mtr_csv()
line_map = {
    "AEL": "機場快綫", "TCL": "東涌綫", "TML": "屯馬綫", "TKL": "將軍澳綫",
    "EAL": "東鐵綫", "SIL": "南港島綫", "TWL": "荃灣綫", "ISL": "港島綫",
    "KTL": "觀塘綫", "DRL": "迪士尼綫"
}

with st.sidebar:
    st.header("⚙️ 選項")
    sel_line = st.selectbox("切換線路", list(line_map.keys()), format_func=lambda x: f"{line_map[x]} ({x})")
    st.write("---")
    st.write("💡 點擊車站名稱查看即時班次")
    auto_refresh = st.checkbox("自動更新數據", value=True)

# 篩選所選路線的車站
line_stations = stations_all[stations_all["Line Code"] == sel_line]

# --- 4. 渲染垂直路線圖 ---
st.subheader(f"{line_map[sel_line]} 沿途各站")
st.caption(f"最後更新：{time.strftime('%H:%M:%S')}")

# 套用路線顏色 CSS
st.markdown(f'<div class="route-container line-{sel_line}">', unsafe_allow_html=True)

# 使用局部更新，防止切換 Expanders 時閃爍
@st.fragment(run_every=10 if auto_refresh else None)
def render_route():
    for _, row in line_stations.iterrows():
        code = row["Station Code"]
        name = row["Chinese Name"]
        
        # 繪製圓點
        st.markdown('<div class="station-dot"></div>', unsafe_allow_html=True)
        
        # 車站點擊區塊 (Expander)
        with st.expander(f"● {name} ({code})"):
            with st.spinner('更新班次中...'):
                api_data = get_mtr_data(sel_line, code)
                display_timetable(api_data, sel_line, code)

render_route()

st.markdown('</div>', unsafe_allow_html=True)