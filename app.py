import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time
import re

# ---------------------------------------------------------
# 1. 核心設定 & CSS (按鈕一致化 + 垂直排列 + 顏色定義)
# ---------------------------------------------------------
st.set_page_config(
    page_title="設備綜合管理系統",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 Session State
if 'active_view' not in st.session_state:
    st.session_state['active_view'] = "ai_search"
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = None
if 'selected_maintain_interval' not in st.session_state:
    st.session_state['selected_maintain_interval'] = None
if 'selected_maintain_model' not in st.session_state:
    st.session_state['selected_maintain_model'] = None
if 'selected_inspect_item' not in st.session_state: # 新增點檢狀態
    st.session_state['selected_inspect_item'] = None
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False # 雖然現在是用頁面跳轉，但保留此變數判斷是否為「修改」狀態
if 'edit_data' not in st.session_state:
    st.session_state['edit_data'] = None
if 'scroll_to_top' not in st.session_state:
    st.session_state['scroll_to_top'] = False
if 'search_input_val' not in st.session_state:
    st.session_state['search_input_val'] = ""

# CSS 設定
st.markdown("""
<style>
    /* 全域字體：全部加粗 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
        font-weight: bold !important;
    }
    
    /* 內容區塊滿版化 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100% !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* === 側邊欄樣式優化：按鈕統一 === */
    div[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    /* 統一所有側邊欄按鈕樣式 */
    div[data-testid="stSidebar"] button {
        width: 100% !important;
        text-align: left !important;
        background-color: white;
        border: 1px solid #E2E8F0;
        margin-bottom: 8px; /* 統一間距 */
        color: #2D3748;
        font-weight: bold;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        height: 48px; /* 統一高度 */
        padding-left: 15px;
        font-size: 1rem;
    }
    
    div[data-testid="stSidebar"] button:hover {
        background-color: #EDF2F7;
        border-color: #CBD5E0;
        color: #2B6CB0;
        transform: translateX(3px);
    }
    
    /* 主功能區標題微調 */
    .sidebar-section-header {
        font-size: 1.2rem;
        font-weight: 900;
        color: #1A202C;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-left: 5px;
        border-left: 4px solid #3182CE;
    }

    /* 選單 Label 加粗 */
    .sidebar-label {
        font-size: 1rem;
        font-weight: 900 !important;
        color: #1A202C;
        margin-bottom: 5px;
        display: block;
    }

    /* 目錄式按鈕 (Radio) */
    div.row-widget.stRadio > div[role="radiogroup"] {
        flex-direction: row;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        border-color: #4A5568;
        transform: translateY(-2px);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #2D3748 !important;
        color: white !important;
        border-color: #1A202C !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    /* 卡片與表格樣式 */
    .topic-container {
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        margin-bottom: 15px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        color: var(--text-color);
    }
    .topic-header {
        background-color: rgba(128,128,128,0.1);
        padding: 10px 15px;
        border-bottom: 1px solid #E2E8F0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .record-row {
        padding: 15px;
        border-bottom: 1px solid rgba(128,128,128,0.1);
    }
    /* AI 精選高亮 */
    .highlight-record {
        background-color: rgba(255, 75, 75, 0.15) !important;
        border-left: 6px solid #ff4b4b !important;
    }
    .badge {
        font-size: 0.8rem;
        padding: 2px 8px;
        border-radius: 4px;
        margin-left: 10px;
        background: rgba(128, 128, 128, 0.2);
    }
    
    /* 清單項目樣式 (通用) */
    .list-item {
        padding: 10px 15px;
        border-bottom: 1px solid #eee;
        display: flex;
        align-items: center;
        background-color: white;
        transition: background-color 0.2s;
    }
    .list-item:hover {
        background-color: #f7fafc;
    }
    .list-icon {
        font-size: 1.2rem; 
        margin-right: 12px;
        width: 24px;
        text-align: center;
    }
    .list-text {
        font-size: 1.1rem; 
        font-weight: bold; 
        color: #2D3748;
    }
    
    /* 顏色定義 */
    .text-red { color: #E53E3E !important; }
    .text-green { color: #38A169 !important; }
    .text-normal { color: #2D3748; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 資料處理 (維修、保養、點檢)
# ---------------------------------------------------------
HAS_AI = False
HAS_FUZZY = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_AI = True
except ImportError:
    HAS_AI = False

try:
    from rapidfuzz import process, fuzz
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False

REPAIR_COLS = ['設備型號', '大標', '主題(事件簡述)', '原因(異常查找、分析)', '處置、應對', '驗證是否排除(驗證作法)', '備註(建議事項及補充事項)']
MAINTAIN_COLS = ['保養類型', '型號', '更換料件']
INSPECT_COLS = ['項目各部', '各部細項'] # 點檢表欄位

# === 顏色規則 (保養用) ===
COLOR_RULES = {
    "420單向軸承": {
        "500K": {
            "red": ["B2476", "B1556", "T2400", "T2670", "D2487", "D2488", "D2510", "D3611", "D2354", "D2355", "D2356", "D2348", "D2349", "D2602", "D2362"],
            "green": []
        },
        "1M": {
            "red": ["B2476", "B1556", "T2400", "T2670", "D2487", "D2488", "D2510", "D3611", "D2354", "D2355", "D2356", "D2348", "D2349", "D2602"],
            "green": ["B1008", "B695", "B992", "B1041", "B1054", "B993", "D3466", "D2642", "D2643", "D2443", "D2674", "D2347", "E2646", "E2647", "D2481", "D2664", "D3496", "D1614", "D3053", "D2449", "D2568", "D2340", "D2567", "D120", "D121"]
        }
    },
    "HGT-421": {
        "500K": {
            "red": ["B1556", "B2476", "T2670", "D3089", "D3090", "D3523", "D3524", "D2602", "D3494", "D3462", "D3463", "D2487", "D2488", "D3254"],
            "green": []
        },
        "1M": {
            "red": ["B1556", "B2476", "T2670", "D3089", "D3090", "D3523", "D3524", "D2602", "D3494", "D3462", "D3463", "D2487", "D2488", "D3254"],
            "green": ["D3530", "D3529", "B695", "B992", "D3213", "D3176", "D3181", "D2514", "D3496", "D2347", "D2510", "D3166", "D3167", "D2798", "D3215", "D2340", "E2646", "E2647", "D2481", "D2664"]
        }
    }
}

def get_part_color_class(part_name, model, interval):
    clean_interval = interval.replace("保養", "").upper().strip()
    if model in COLOR_RULES and clean_interval in COLOR_RULES[model]:
        rules = COLOR_RULES[model][clean_interval]
        for key in rules["red"]:
            if key in part_name: return "text-red", "🔴"
        for key in rules["green"]:
            if key in part_name: return "text-green", "🟢"
    return "text-normal", "🔩"

def clean_text(text):
    if not isinstance(text, str): return str(text)
    text = text.replace("**", "")
    text = text.replace("\n", " ").strip()
    return text

def expand_query(query):
    SYNONYMS = {
        "聲音": "異音 噪音 吵雜 聲響", "怪聲": "異音 磨損",
        "不動": "卡死 異常 停止 無法運作失效", "壞掉": "異常 故障 損壞",
        "溫度": "過熱 發燙 高溫", "漏水": "洩漏 滲水",
        "轉速": "速度 變慢", "sensor": "感應器 光電",
        "馬達": "motor", "皮帶": "斷裂 磨損",
        "飛板": "fly board 驅動板", 
    }
    q = query
    for k, v in SYNONYMS.items():
        if k in query.lower(): q += " " + v
    return q

def get_google_sheet_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=5)
def load_repair_data():
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheets"]["repair_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=REPAIR_COLS)
        for col in REPAIR_COLS:
            if col not in df.columns: df[col] = "無"
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        df['original_id'] = df.index
        df['search_content'] = (
            (df['設備型號'] + " ") * 2 + 
            (df['主題(事件簡述)'] + " ") * 5 + 
            (df['原因(異常查找、分析)'] + " ") * 3 + 
            df['處置、應對']
        )
        return df
    except Exception as e:
        return pd.DataFrame(columns=REPAIR_COLS)

@st.cache_data(ttl=60)
def load_maintain_data():
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheets"]["maintain_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        rows = worksheet.get_all_values()
        if not rows: return pd.DataFrame(columns=MAINTAIN_COLS)
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        df.replace("", float("NaN"), inplace=True)
        df['保養類型'] = df['保養類型'].ffill()
        df['型號'] = df['型號'].ffill()
        df['保養類型'] = df['保養類型'].astype(str).str.upper().str.strip()
        df = df.dropna(subset=['更換料件'])
        df.fillna("", inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=MAINTAIN_COLS)

# === 新增：讀取點檢表 ===
@st.cache_data(ttl=60)
def load_inspect_data():
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheets"]["inspect_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        rows = worksheet.get_all_values()
        if not rows: return pd.DataFrame(columns=INSPECT_COLS)
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        # 處理合併儲存格
        df.replace("", float("NaN"), inplace=True)
        df['項目各部'] = df['項目各部'].ffill()
        df.fillna("", inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=INSPECT_COLS)

def save_repair_data(df):
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheets"]["repair_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        cols_to_save = [c for c in df.columns if c in REPAIR_COLS]
        df_save = df[cols_to_save]
        data_to_write = [df_save.columns.values.tolist()] + df_save.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_write)
        load_repair_data.clear()
        return True
    except Exception as e:
        st.error(f"存檔失敗: {e}")
        return False

def delete_repair_data(index_to_delete):
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheets"]["repair_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        worksheet.delete_rows(index_to_delete + 2)
        load_repair_data.clear()
        return True
    except Exception as e:
        st.error(f"刪除失敗: {e}")
        return False

@st.cache_resource
def build_search_engine(df_content):
    if not HAS_AI or df_content.empty: return None, None
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(1, 3))
    tfidf_matrix = vectorizer.fit_transform(df_content)
    return vectorizer, tfidf_matrix

def super_smart_search(query, df, vectorizer, tfidf_matrix):
    if not query or df.empty: return pd.DataFrame(), "", ""
    smart_query = expand_query(query)
    scores = pd.Series([0.0] * len(df))
    if HAS_AI and vectorizer:
        try:
            query_vec = vectorizer.transform([smart_query])
            vec_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
            scores += vec_scores * 0.6 
        except: pass
    if HAS_FUZZY:
        fuzzy_scores_topic = df['主題(事件簡述)'].apply(lambda x: fuzz.token_set_ratio(query, x) / 100.0)
        fuzzy_scores_cause = df['原因(異常查找、分析)'].apply(lambda x: fuzz.token_set_ratio(query, x) / 100.0)
        scores += (fuzzy_scores_topic * 0.3 + fuzzy_scores_cause * 0.1)
    keywords = query.split()
    keyword_mask = pd.Series([0.0] * len(df))
    for k in keywords:
        if len(k) > 1:
            keyword_mask += df['search_content'].str.contains(k, case=False, regex=False).astype(float)
    scores += keyword_mask * 0.2
    df_res = df.copy()
    df_res['final_score'] = scores
    results = df_res[df_res['final_score'] > 0.15].sort_values('final_score', ascending=False).head(10)
    summary_md = ""
    external_link = ""
    if not results.empty:
        best_row = None
        for _, row in results.iterrows():
            cause_text = str(row['原因(異常查找、分析)']).strip()
            if len(cause_text) > 2 and cause_text not in ["無", "待處理", "未知", "nan"]:
                best_row = row
                break
        if best_row is None: best_row = results.iloc[0]
        clean_cause = clean_text(best_row['原因(異常查找、分析)'])
        clean_topic = clean_text(best_row['主題(事件簡述)'])
        summary_md = f"""
        <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; border-left: 5px solid #3182CE;">
            <h4 style="margin-top:0;">🤖 AI 診斷報告</h4>
            <p>分析您的描述，資料庫中最相似的案例為 <b>「{clean_topic}」</b>。</p>
            <p>👉 <b>建議檢查方向：</b><br>
            <span style="color: var(--text-color); font-size: 1.1em; opacity: 0.9;">{clean_cause if len(clean_cause) > 1 else "暫無明確內部紀錄，建議參考下方外部搜尋。"}</span>
            </p>
        </div>
        """
        search_term = f"{best_row['設備型號']} {clean_topic} 故障排除"
        external_link = f"https://www.google.com/search?q={search_term}"
    else:
        summary_md = """
        <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; border-left: 5px solid #718096;">
            🤖 目前資料庫中找不到相似度夠高的案例。
        </div>
        """
        external_link = f"https://www.google.com/search?q=設備維修 {query}"
    return results, summary_md, external_link

# ---------------------------------------------------------
# 3. 頁面控制與表單 (改用 View 跳轉)
# ---------------------------------------------------------
def set_view(view_name):
    st.session_state['active_view'] = view_name
    # 離開維修履歷時清除暫存
    if view_name != 'repair_log' and view_name != 'add_edit_repair':
        st.session_state['target_case_id'] = None

def jump_to_repair_case(model_name, case_id, category, topic):
    st.session_state['active_view'] = "repair_log"
    st.session_state['selected_model'] = model_name
    st.session_state['target_case_id'] = case_id 

# ---------------------------------------------------------
# 4. 主程式執行
# ---------------------------------------------------------
def main():
    df_repair = load_repair_data()
    df_maintain = load_maintain_data()
    df_inspect = load_inspect_data()
    
    vectorizer, tfidf_matrix = build_search_engine(df_repair['search_content'])
    
    # 資料清單
    all_repair_models = sorted(list(set(df_repair['設備型號'].astype(str).tolist()))) if not df_repair.empty else []
    maintain_intervals = sorted(list(set(df_maintain['保養類型'].astype(str).tolist()))) if not df_maintain.empty else []
    inspect_items = sorted(list(set(df_inspect['項目各部'].astype(str).tolist()))) if not df_inspect.empty else []

    # === 側邊欄設計 ===
    with st.sidebar:
        st.markdown('<div class="sidebar-section-header">🎛️ 中控台</div>', unsafe_allow_html=True)
        
        # 垂直排列按鈕 (統一寬高)
        if st.button("🧠 AI 智能診斷"): set_view("ai_search")
        if st.button("📊 全域戰情室"): set_view("dashboard")
        
        # 新增與修改共用同一個 View
        if st.button("➕ 新增/編輯紀錄"):
            st.session_state['edit_mode'] = False # 新增模式
            st.session_state['edit_data'] = None
            set_view("add_edit_repair")
            st.rerun()
            
        st.divider()
        
        # === 1. 設備目錄 (下拉選單) ===
        with st.expander("📂 設備維修目錄", expanded=False):
            st.markdown('<span class="sidebar-label">選擇機型查閱履歷</span>', unsafe_allow_html=True)
            selected_model_dd = st.selectbox(
                "選擇機型",
                ["請選擇..."] + all_repair_models,
                index=0,
                key="sb_repair_model",
                label_visibility="collapsed"
            )
            if selected_model_dd != "請選擇...":
                # 按下按鈕後自動跳轉
                if st.button("🔍 查詢履歷"):
                    st.session_state['selected_model'] = selected_model_dd
                    st.session_state['target_category'] = "全部顯示"
                    st.session_state['target_topic'] = "全部顯示"
                    set_view("repair_log")
                    st.rerun()

        # === 2. 保養目錄 ===
        with st.expander("🛠️ 定期保養目錄", expanded=False):
            st.markdown('<span class="sidebar-label">1. 選擇保養里程</span>', unsafe_allow_html=True)
            sel_interval = st.selectbox(
                "選擇保養里程",
                ["請選擇..."] + maintain_intervals,
                key="sb_maintain_interval",
                label_visibility="collapsed"
            )
            
            maintain_models = []
            if sel_interval != "請選擇...":
                maintain_models = sorted(list(set(
                    df_maintain[df_maintain['保養類型'] == sel_interval]['型號'].astype(str).tolist()
                )))
            
            st.markdown('<span class="sidebar-label">2. 選擇機型</span>', unsafe_allow_html=True)
            sel_m_model = st.selectbox(
                "選擇機型",
                ["請選擇..."] + maintain_models,
                key="sb_maintain_model",
                disabled=(sel_interval == "請選擇..."),
                label_visibility="collapsed"
            )
            
            if sel_m_model != "請選擇...":
                if st.button("📋 查看料件"):
                    st.session_state['selected_maintain_interval'] = sel_interval
                    st.session_state['selected_maintain_model'] = sel_m_model
                    set_view("maintenance_log")
                    st.rerun()

        # === 3. 點檢目錄 (New!) ===
        with st.expander("📋 點檢基準目錄", expanded=False):
            st.markdown('<span class="sidebar-label">選擇項目各部</span>', unsafe_allow_html=True)
            sel_inspect_item = st.selectbox(
                "選擇項目",
                ["請選擇..."] + inspect_items,
                key="sb_inspect_item",
                label_visibility="collapsed"
            )
            if sel_inspect_item != "請選擇...":
                if st.button("👁️ 查看細節"):
                    st.session_state['selected_inspect_item'] = sel_inspect_item
                    set_view("inspect_log")
                    st.rerun()

    # --- 畫面路由 ---

    # 1. AI 搜尋
    if st.session_state['active_view'] == "ai_search":
        st.markdown('<h1>🧠 設備維修智慧搜尋 <span style="font-size:1rem; color:gray;">(自動遞補最佳建議)</span></h1>', unsafe_allow_html=True)
        query = st.text_input("💬 故障描述", placeholder="試試看輸入：馬達異音、皮帶斷裂...", value=st.session_state['search_input_val'])
        if query != st.session_state['search_input_val']:
            st.session_state['search_input_val'] = query
            st.rerun()
        if query:
            with st.spinner("⚡ AI 深度檢索 & 外部資源比對中..."):
                results, summary_html, ext_link = super_smart_search(query, df_repair, vectorizer, tfidf_matrix)
            st.markdown(summary_html, unsafe_allow_html=True)
            if ext_link:
                st.write("")
                st.link_button("🌐 點此搜尋 Google 外部相關案例 (AI 生成關鍵字)", ext_link, type="secondary")
            if not results.empty:
                st.markdown("### 📋 內部相似案例")
                for i, row in results.iterrows():
                    score_display = f"相似度: {int(row['final_score']*100)}%" if 'final_score' in row else ""
                    st.markdown(f"""
                    <div class="topic-container" style="padding:15px; border-left:5px solid #3182CE;">
                        <div style="display:flex; justify-content:space-between;">
                            <h3 style="margin:0; font-size:1.1rem;">🔧 {row['主題(事件簡述)']}</h3>
                            <span style="font-size:0.8rem; background:rgba(128,128,128,0.2); padding:2px 8px; border-radius:10px;">{score_display}</span>
                        </div>
                        <div style="margin-top:8px; opacity:0.9;">
                            <span style="background:rgba(128,128,128,0.1); padding:2px 6px; border-radius:4px; font-size:0.8rem;">{row['設備型號']}</span>
                            <br><br>
                            <b>🔴 原因：</b>{clean_text(str(row['原因(異常查找、分析)']))[:50]}...<br>
                            <b>🟢 對策：</b>{clean_text(str(row['處置、應對']))[:50]}...
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 開啟此案例", key=f"jump_{i}"):
                        jump_to_repair_case(row['設備型號'], row['original_id'], row['大標'], row['主題(事件簡述)'])
                        st.rerun()

    # 2. 戰情室
    elif st.session_state['active_view'] == "dashboard":
        st.markdown('<h1>📊 全域戰情室</h1>', unsafe_allow_html=True)
        if df_repair.empty:
            st.warning("目前無資料")
        else:
            with st.expander("⚙️ 圖表資料篩選", expanded=True):
                selected_models_chart = st.multiselect("選擇分析機型 (預設全選，可點擊 X 移除)", all_repair_models, default=all_repair_models)
                df_chart = df_repair[df_repair['設備型號'].isin(selected_models_chart)]
            st.divider()
            if not df_chart.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("案件數", len(df_chart))
                m2.metric("機型數", df_chart['設備型號'].nunique())
                m3.metric("分類數", df_chart['大標'].nunique())
                COLOR_PALETTE = ['#334155', '#0F766E', '#1E40AF', '#3730A3', '#166534', '#9A3412']
                st.markdown("### 🟠 設備異常總覽 (矩形圖)")
                df_treemap = df_chart.copy()
                def split_text(text): return "<br>".join([str(text)[i:i+6] for i in range(0, len(str(text)), 6)])
                df_treemap['display_text'] = df_treemap['主題(事件簡述)'].apply(split_text)
                fig_tree = px.treemap(df_treemap, path=[px.Constant("全廠"), '設備型號', '大標', 'display_text'], color='大標', color_discrete_sequence=COLOR_PALETTE)
                fig_tree.update_traces(textinfo="label+value", textposition="middle center", textfont=dict(size=16, family="Microsoft JhengHei", color="white", weight='bold'), hovertemplate='<b>%{label}</b><br>次數: %{value}<extra></extra>', marker=dict(line=dict(width=1, color='white')))
                fig_tree.update_layout(margin=dict(t=50, l=10, r=10, b=10), height=600, uniformtext=dict(minsize=10, mode=False))
                st.plotly_chart(fig_tree, use_container_width=True)
                st.divider()
                st.markdown("### 🔥 Top 20 高頻異常原因")
                top_issues = df_chart['主題(事件簡述)'].value_counts().head(20).reset_index()
                top_issues.columns = ['主題', '次數']
                fig_bar = px.bar(top_issues, x='次數', y='主題', orientation='h', text='次數', color='次數', color_continuous_scale='Greys')
                fig_bar.update_traces(textfont=dict(weight='bold', size=14), marker_line_color='rgb(8,48,107)', marker_line_width=1, opacity=0.9)
                fig_bar.update_layout(yaxis=dict(autorange="reversed", tickfont=dict(weight='bold')), xaxis=dict(title="發生次數", tickfont=dict(weight='bold')), height=600, coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)

    # 3. 維修履歷
    elif st.session_state['active_view'] == "repair_log":
        target_model = st.session_state['selected_model']
        target_id = st.session_state['target_case_id']
        target_cat = st.session_state.get('target_category', "全部顯示")
        target_topic = st.session_state.get('target_topic', "全部顯示")
        
        if not target_model:
            st.warning("⚠️ 請從側邊欄選擇機型")
            st.stop()
            
        st.markdown(f'<h1>📄 {target_model} 維修履歷</h1>', unsafe_allow_html=True)
        df_model = df_repair[df_repair['設備型號'] == target_model]
        
        st.markdown("### 1️⃣ 選擇分類")
        all_cats = sorted(list(set(df_model['大標'].tolist())))
        cats_display = ["全部顯示"] + all_cats
        idx_cat = cats_display.index(target_cat) if target_cat in cats_display else 0
        sel_cat = st.radio("大標", cats_display, index=idx_cat, horizontal=True, label_visibility="collapsed", key="cat_filter")
        st.session_state['target_category'] = sel_cat
        df_l1 = df_model if sel_cat == "全部顯示" else df_model[df_model['大標'] == sel_cat]

        if not df_l1.empty:
            st.divider()
            st.markdown("### 2️⃣ 選擇主題")
            all_topics = sorted(list(set(df_l1['主題(事件簡述)'].tolist())))
            topics_display = ["全部顯示"] + all_topics
            idx_topic = topics_display.index(target_topic) if target_topic in topics_display else 0
            sel_topic = st.radio("主題", topics_display, index=idx_topic, horizontal=True, label_visibility="collapsed", key="topic_filter")
            st.session_state['target_topic'] = sel_topic
            df_final = df_l1 if sel_topic == "全部顯示" else df_l1[df_l1['主題(事件簡述)'] == sel_topic]
        else:
            df_final = pd.DataFrame()
            
        st.divider()
        if df_final.empty:
            st.info("此分類下無資料")
        else:
            if target_id is not None:
                target_row = df_final[df_final['original_id'] == target_id]
                other_rows = df_final[df_final['original_id'] != target_id]
                df_final = pd.concat([target_row, other_rows])

            grouped = df_final.groupby('主題(事件簡述)', sort=False)
            
            for topic_name, group_data in grouped:
                st.markdown(f"""<div class="topic-container"><div class="topic-header"><span>📌 {topic_name}</span><span class="badge">{len(group_data)} 筆紀錄</span></div>""", unsafe_allow_html=True)
                for idx, row in group_data.iterrows():
                    is_target = (row['original_id'] == target_id)
                    row_class = "highlight-record" if is_target else ""
                    target_icon = "✅ [AI精選]" if is_target else ""
                    with st.container():
                        c_content, c_edit = st.columns([0.92, 0.08])
                        with c_content:
                            st.markdown(f"""<div class="record-row {row_class}" style="border-bottom:none; padding-bottom:5px;"><div style="font-weight:bold; color:#ff4b4b; margin-bottom:5px;">{target_icon}</div><div style="display: flex; flex-wrap: wrap; gap: 20px;"><div style="flex: 2; min-width: 300px;"><p><strong style="color:#c53030;">🔴 原因：</strong> {clean_text(row['原因(異常查找、分析)'])}</p><p><strong style="color:#2f855a;">🟢 對策：</strong> {clean_text(row['處置、應對'])}</p></div><div style="flex: 1; min-width: 200px; border-left: 3px solid rgba(128,128,128,0.2); padding-left: 15px; font-size: 0.9em; opacity:0.8;"><p><b>驗證：</b> {row['驗證是否排除(驗證作法)']}</p><p><b>備註：</b> {row['備註(建議事項及補充事項)']}</p></div></div></div>""", unsafe_allow_html=True)
                        with c_edit:
                            st.write(""); st.write("")
                            # ★ 修改：按下編輯直接跳轉頁面 ★
                            if st.button("✏️", key=f"edit_btn_{row['original_id']}"):
                                st.session_state['edit_mode'] = True
                                st.session_state['edit_data'] = row.to_dict()
                                set_view("add_edit_repair")
                                st.rerun()
                    st.markdown("<hr style='margin:0; border:0; border-top:1px solid rgba(128,128,128,0.1);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # 4. 保養資料
    elif st.session_state['active_view'] == "maintenance_log":
        m_interval = st.session_state['selected_maintain_interval']
        m_model = st.session_state['selected_maintain_model']
        st.markdown(f'<h1>🛠️ 保養料件清單</h1>', unsafe_allow_html=True)
        st.info(f"當前檢視：**{m_interval}** - **{m_model}**")
        df_m_show = df_maintain[(df_maintain['保養類型'] == m_interval) & (df_maintain['型號'] == m_model)]
        if df_m_show.empty:
            st.warning("⚠️ 查無此機型的保養料件資料")
        else:
            parts_list = df_m_show['更換料件'].tolist()
            st.markdown('<div style="background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 5px;">', unsafe_allow_html=True)
            for part in parts_list:
                items = part.split('\n')
                for item in items:
                    item_clean = item.strip()
                    if item_clean:
                        color_class, icon = get_part_color_class(item_clean, m_model, m_interval)
                        st.markdown(f"""<div class="list-item"><span class="list-icon">{icon}</span><span class="list-text {color_class}">{item_clean}</span></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("⬅️ 返回中控台"):
                set_view("ai_search")
                st.rerun()

    # 5. 點檢資料 (New!)
    elif st.session_state['active_view'] == "inspect_log":
        i_item = st.session_state['selected_inspect_item']
        st.markdown(f'<h1>📋 {i_item} - 點檢細節</h1>', unsafe_allow_html=True)
        
        df_i_show = df_inspect[df_inspect['項目各部'] == i_item]
        
        if df_i_show.empty:
            st.warning("⚠️ 查無資料")
        else:
            details_list = df_i_show['各部細項'].tolist()
            st.markdown('<div style="background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 5px;">', unsafe_allow_html=True)
            for detail in details_list:
                lines = str(detail).split('\n')
                for line in lines:
                    line_clean = line.strip()
                    if line_clean:
                        st.markdown(f"""
                        <div class="list-item">
                            <span class="list-icon">🔍</span>
                            <span class="list-text text-normal">{line_clean}</span>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("⬅️ 返回中控台"):
                set_view("ai_search")
                st.rerun()

    # 6. 新增/編輯 維修紀錄 (專屬頁面)
    elif st.session_state['active_view'] == "add_edit_repair":
        is_edit = st.session_state['edit_mode']
        form_title = "📝 編輯維修紀錄" if is_edit else "➕ 新增維修紀錄"
        st.markdown(f"<h1>{form_title}</h1>", unsafe_allow_html=True)
        
        # 準備資料
        existing_models = sorted(list(set(df_repair['設備型號'].astype(str).tolist()))) if not df_repair.empty else []
        existing_cats = sorted(list(set(df_repair['大標'].astype(str).tolist()))) if not df_repair.empty else []
        model_options = existing_models + ["➕ 手動輸入"]
        cat_options = existing_cats + ["➕ 手動輸入"]
        
        default_data = st.session_state['edit_data'] if is_edit else {}
        
        # 互動式選單 (不在 Form 內)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📍 設備型號")
            curr_model = default_data.get('設備型號', existing_models[0] if existing_models else "")
            idx_model = existing_models.index(curr_model) if curr_model in existing_models else len(model_options) - 1
            sel_model = st.selectbox("設備型號選擇", model_options, index=idx_model, label_visibility="collapsed")
            final_model = st.text_input("輸入新設備型號", value=curr_model if curr_model not in existing_models else "") if sel_model == "➕ 手動輸入" else sel_model

        with col2:
            st.markdown("##### 🏷️ 分類 (大標)")
            curr_cat = default_data.get('大標', existing_cats[0] if existing_cats else "")
            idx_cat = existing_cats.index(curr_cat) if curr_cat in existing_cats else len(cat_options) - 1
            sel_cat = st.selectbox("大標選擇", cat_options, index=idx_cat, label_visibility="collapsed")
            final_cat = st.text_input("輸入新分類", value=curr_cat if curr_cat not in existing_cats else "") if sel_cat == "➕ 手動輸入" else sel_cat

        st.write("")
        
        with st.form("add_edit_form"):
            new_topic = st.text_area("📝 主題 (事件簡述 - 必填)", value=default_data.get('主題(事件簡述)', ""), height=68)
            col_cause, col_sol = st.columns(2)
            with col_cause:
                new_cause = st.text_area("🔴 原因 (異常查找、分析)", value=default_data.get('原因(異常查找、分析)', ""), height=200)
            with col_sol:
                new_sol = st.text_area("🟢 處置、應對", value=default_data.get('處置、應對', ""), height=200)
            
            col_ver, col_rem = st.columns(2)
            with col_ver:
                new_ver = st.text_area("驗證是否排除", value=default_data.get('驗證是否排除(驗證作法)', ""), height=100)
            with col_rem:
                new_rem = st.text_area("備註", value=default_data.get('備註(建議事項及補充事項)', ""), height=100)
            
            st.markdown("---")
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                submitted = st.form_submit_button("💾 儲存紀錄", type="primary", use_container_width=True)
            with c2:
                # 取消按鈕 (雖然 form 裡面無法直接跳轉，但可以透過 callback 或 rerun 處理，這裡簡單做)
                cancel = st.form_submit_button("❌ 取消")
            
            # 刪除按鈕 (只在編輯模式出現)
            delete_check = False
            if is_edit:
                with c3:
                    st.write("") # Spacer
                    delete_check = st.checkbox("🗑️ 刪除此紀錄", key="del_check")

            if cancel:
                set_view("repair_log" if is_edit else "ai_search")
                st.rerun()

            if submitted:
                if is_edit and delete_check:
                    with st.spinner("🗑️ 正在刪除..."):
                        if delete_repair_data(default_data['original_id']):
                            st.success("已刪除！")
                            time.sleep(1)
                            set_view("repair_log")
                            st.rerun()
                elif not final_model or not new_topic:
                    st.error("⚠️ 「設備型號」與「主題」為必填欄位！")
                else:
                    new_record = {
                        '設備型號': final_model,
                        '大標': final_cat,
                        '主題(事件簡述)': new_topic,
                        '原因(異常查找、分析)': new_cause,
                        '處置、應對': new_sol,
                        '驗證是否排除(驗證作法)': new_ver,
                        '備註(建議事項及補充事項)': new_rem
                    }
                    
                    with st.spinner("💾 正在儲存到 Google Sheet..."):
                        # 更新 DataFrame
                        if is_edit:
                            target_idx = default_data['original_id']
                            for key, val in new_record.items(): df_repair.at[target_idx, key] = val
                        else:
                            new_row_df = pd.DataFrame([new_record])
                            df_repair = pd.concat([df_repair, new_row_df], ignore_index=True)
                        
                        # 寫入雲端
                        if save_repair_data(df_repair):
                            st.success("✅ 儲存成功！")
                            time.sleep(1)
                            # 儲存後跳轉回列表查看
                            st.session_state['selected_model'] = final_model
                            set_view("repair_log")
                            st.rerun()

if __name__ == "__main__":
    main()
