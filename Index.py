import streamlit as st
import requests
import pandas as pd
import time
import os

# 設定頁面
st.set_page_config(page_title="港鐵即時到站路線圖", layout="centered")

# --- 1. 自定義 CSS：打造垂直路線圖視覺 ---
st.markdown("""
    <style>
    .line-segment {
        width: 6px;
        height: 50px;
        margin-left: 20px;
        background-color: #888;
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
    div.stButton > button {
        border: none;
        background: transparent;
        color: #31333F;
        font-size: 18px;
        font-weight: 500;
        text-align: left;
        width: 100%;
        padding: 10px 20px;
    }
    div.stButton > button:hover {
        color: #FF4B4B;
        background: #F0F2F6;
    }
    .eta-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #0078d4;
        margin: 5px 0px 20px 40px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 數據載入 (修復路徑問題) ---
@st.cache_data
def load_mtr_csv():
    # 關鍵修復：取得此腳本所在的絕對路徑，再組合檔案名稱
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "mtr_lines_and_stations.csv")
    
    if not os.path.exists(file_path):
        st.error(f"找不到檔案：{file_path}。請確認檔名大小寫是否完全一致。")
        return pd.DataFrame()
    return pd.read_csv(file_path)

def get_mtr_eta(line, sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=zh"
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# --- 3. UI 介面設定 ---
st.title("🚇 港鐵動態路線圖")

stations_all = load_mtr_csv()

if not stations_all.empty:
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
        if st.button("🔄 刷新數據"):
            st.rerun()

    # 篩選並排序車站
    line_data = stations_all[stations_all["Line Code"] == sel_line_code].sort_values("Sequence")
    line_stations = line_data.drop_duplicates(subset=["Station Code"])
    line_color = line_map[sel_line_code]['color']

    st.subheader(f"{line_map[sel_line_code]['name']} 沿途各站")
    
    # 使用 Session State 記憶點擊的車站
    if "active_sta" not in st.session_state:
        st.session_state.active_sta = None

    for _, row in line_stations.iterrows():
        sta_code = row["Station Code"]
        sta_name = row["Chinese Name"]
        
        col_line, col_name = st.columns([0.1, 0.9])
        with col_line:
            st.markdown(f'<div class="line-segment" style="background-color: {line_color};"><div class="station-node" style="border-color: {line_color};"></div></div>', unsafe_allow_html=True)
        
        with col_name:
            if st.button(sta_name, key=f"btn_{sta_code}"):
                st.session_state.active_sta = sta_code
        
        # 展開顯示班次
        if st.session_state.active_sta == sta_code:
            with st.spinner(f"正在抓取 {sta_name} 即時資訊..."):
                eta_data = get_mtr_eta(sel_line_code, sta_code)
                if eta_data and eta_data.get("status") == 1:
                    res = eta_data.get("data", {}).get(f"{sel_line_code}-{sta_code}", {})
                    st.markdown('<div class="eta-box">', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    for i, direction in enumerate(["UP", "DOWN"]):
                        trains = res.get(direction, [])
                        with (c1 if i==0 else c2):
                            st.write(f"**{'⬆️ 上行' if direction=='UP' else '⬇️ 下行'}**")
                            if not trains: st.write("末班車已過或無資訊")
                            for t in trains:
                                st.write(f"⏱️ {t['time'].split(' ')[1][:5]} - 往 {t['dest']}")
                    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("請確認 CSV 檔案是否正確放置於目錄中。")