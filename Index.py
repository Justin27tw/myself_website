import streamlit as st
import requests
import pandas as pd
import time
import os

# 設定頁面
st.set_page_config(page_title="港鐵即時到站路線圖", layout="centered")

# --- 1. 自定義 CSS：打造垂直路線圖視覺與強制白底 ---
st.markdown("""
    <style>
    /* 強制亮色背景主題 */
    .stApp {
        background-color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] {
        background-color: #F4F6F9 !important;
    }
    html, body, p, h1, h2, h3, h4, h5, h6, span {
        color: #333333 !important;
    }
    
    /* 路線圖視覺元素 */
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
        color: #333333 !important;
        font-size: 18px;
        font-weight: 500;
        text-align: left;
        width: 100%;
        padding: 10px 20px;
    }
    div.stButton > button:hover {
        color: #FF4B4B !important;
        background: #F0F2F6 !important;
    }
    .eta-box {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #0078d4;
        margin: 5px 0px 20px 40px;
        color: #333333;
    }
    </style>
""", unsafe_allow_html=True)

# --- 定義各路線的強制排序字典 ---
CUSTOM_ORDER = {
    "KTL": ["黃埔", "何文田", "油麻地", "旺角", "太子", "石硤尾", "九龍塘", "樂富", "黃大仙", "鑽石山", "彩虹", "九龍灣", "牛頭角", "觀塘", "藍田", "油塘", "調景嶺"],
    "TWL": ["中環", "金鐘", "尖沙咀", "佐敦", "油麻地", "旺角", "太子", "深水埗", "長沙灣", "荔枝角", "美孚", "荔景", "葵芳", "葵興", "大窩口", "荃灣"],
    "ISL": ["堅尼地城", "香港大學", "西營盤", "上環", "中環", "金鐘", "灣仔", "銅鑼灣", "天后", "炮台山", "北角", "鰂魚涌", "太古", "西灣河", "筲箕灣", "杏花邨", "柴灣"],
    "TKL": ["北角", "鰂魚涌", "油塘", "調景嶺", "將軍澳", "坑口", "寶琳", "康城"],
    "TML": ["屯門", "兆康", "天水圍", "朗屏", "元朗", "錦上路", "荃灣西", "美孚", "南昌", "柯士甸", "尖東", "紅磡", "何文田", "土瓜灣", "宋皇台", "啟德", "鑽石山", "顯徑", "大圍", "車公廟", "沙田圍", "第一城", "石門", "大水坑", "恆安", "馬鞍山", "烏溪沙"],
    "EAL": ["金鐘", "會展", "紅磡", "旺角東", "九龍塘", "大圍", "沙田", "火炭", "馬場", "大學", "大埔墟", "太和", "粉嶺", "上水", "羅湖", "落馬洲"],
    "TCL": ["香港", "九龍", "奧運", "南昌", "荔景", "青衣", "欣澳", "東涌"],
    "SIL": ["金鐘", "海洋公園", "黃竹坑", "利東", "海怡半島"],
    "AEL": ["香港", "九龍", "青衣", "機場", "博覽館"],
    "DRL": ["欣澳", "迪士尼"]
}


# --- 2. 數據載入與轉換表建立 ---
@st.cache_data
def load_mtr_data():
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "mtr_lines_and_stations.csv")
    
    if not os.path.exists(file_path):
        st.error(f"找不到檔案：{file_path}，請檢查檔案是否已上傳。")
        return pd.DataFrame(), {}
    
    df = pd.read_csv(file_path)
    mapping = df.drop_duplicates(subset=["Station Code"]).set_index("Station Code")["Chinese Name"].to_dict()
    
    return df, mapping

def get_mtr_eta(line, sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={sta}&lang=zh"
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# --- 3. 初始化數據 ---
stations_all, station_mapping = load_mtr_data()

st.title("🚇 港鐵動態路線圖")

if not stations_all.empty:
    line_info = {
        "KTL": {"name": "觀塘綫", "color": "#00AB4E"},
        "TWL": {"name": "荃灣綫", "color": "#E2231A"},
        "ISL": {"name": "港島綫", "color": "#0077C8"},
        "TKL": {"name": "將軍澳綫", "color": "#A35EB5"},
        "TML": {"name": "屯馬綫", "color": "#9A3820"},
        "EAL": {"name": "東鐵綫", "color": "#53B7E8"},
        "TCL": {"name": "東涌綫", "color": "#F3A11F"},
        "SIL": {"name": "南港島綫", "color": "#B5BD00"},
        "AEL": {"name": "機場快綫", "color": "#007078"},
        "DRL": {"name": "迪士尼綫", "color": "#F5821F"}
    }

    with st.sidebar:
        st.header("⚙️ 選項")
        sel_line_code = st.selectbox("切換線路", list(line_info.keys()), 
                                    format_func=lambda x: f"{line_info[x]['name']} ({x})")
        if st.button("🔄 刷新資訊"):
            st.rerun()

    # 獲取該線路車站
    line_stations = stations_all[stations_all["Line Code"] == sel_line_code].copy()
    line_stations = line_stations.drop_duplicates(subset=["Station Code"])
    
    # 依照 CUSTOM_ORDER 進行強制排序
    if sel_line_code in CUSTOM_ORDER:
        # 建立排序字典
        sort_mapping = {name: index for index, name in enumerate(CUSTOM_ORDER[sel_line_code])}
        # 產生一個暫時的排序欄位，若找不到則給予極大值排在最後
        line_stations['Custom_Sort'] = line_stations['Chinese Name'].map(sort_mapping).fillna(999)
        line_stations = line_stations.sort_values("Custom_Sort").drop(columns=["Custom_Sort"])
    else:
        # 如果意外有沒被包含的路線，則使用原本的 Sequence 備用
        line_stations = line_stations.sort_values("Sequence")

    line_color = line_info[sel_line_code]['color']

    st.subheader(f"{line_info[sel_line_code]['name']} 路線圖")
    
    if "active_sta" not in st.session_state:
        st.session_state.active_sta = None

    # --- 4. 渲染垂直路線圖 ---
    for _, row in line_stations.iterrows():
        sta_code = row["Station Code"]
        sta_name = row["Chinese Name"]
        
        col_line, col_name = st.columns([0.1, 0.9])
        with col_line:
            st.markdown(f'''
                <div class="line-segment" style="background-color: {line_color};">
                    <div class="station-node" style="border-color: {line_color};"></div>
                </div>''', unsafe_allow_html=True)
        
        with col_name:
            if st.button(sta_name, key=f"btn_{sta_code}"):
                st.session_state.active_sta = sta_code
        
        # 顯示點擊後的即時班次
        if st.session_state.active_sta == sta_code:
            with st.spinner(f"正在更新 {sta_name} 班次..."):
                eta_data = get_mtr_eta(sel_line_code, sta_code)
                if eta_data and eta_data.get("status") == 1:
                    res = eta_data.get("data", {}).get(f"{sel_line_code}-{sta_code}", {})
                    st.markdown('<div class="eta-box">', unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    for i, direction in enumerate(["UP", "DOWN"]):
                        trains = res.get(direction, [])
                        with (c1 if i==0 else c2):
                            st.write(f"**{'⬆️ 上行' if direction=='UP' else '⬇️ 下行'}**")
                            if not trains:
                                st.write("目前無即時資訊")
                            for t in trains:
                                # 這裡執行代碼轉中文名稱
                                dest_code = t.get('dest', '')
                                dest_chinese = station_mapping.get(dest_code, dest_code) # 找不到就顯示原代碼
                                
                                arrival_time = t['time'].split(' ')[1][:5]
                                st.write(f"⏱️ {arrival_time} 往 **{dest_chinese}** (月台{t['plat']})")
                    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("等待數據載入中...")