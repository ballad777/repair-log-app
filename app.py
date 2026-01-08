import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import re

# ---------------------------------------------------------
# 1. 核心設定 & 終極 CSS (電腦/手機雙向優化)
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
if 'selected_inspect_item' not in st.session_state:
    st.session_state['selected_inspect_item'] = None
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
if 'edit_data' not in st.session_state:
    st.session_state['edit_data'] = None
if 'scroll_to_top' not in st.session_state:
    st.session_state['scroll_to_top'] = False
if 'search_input_val' not in st.session_state:
    st.session_state['search_input_val'] = ""

# CSS 設定
st.markdown("""
<style>
    /* === 1. 全域字體與基礎設定 === */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
        font-weight: bold !important;
    }

    /* === 2. 響應式容器設計 (關鍵修復) === */
    /* 電腦版預設 */
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100% !important;
    }

    /* 手機版適配 (螢幕小於 768px) */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 2rem;     /* 減少頂部留白 */
            padding-left: 0.5rem;  /* 減少左右留白，爭取空間 */
            padding-right: 0.5rem;
        }
        /* 強制標題在手機上變小一點 */
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.4rem !important; }
        h3 { font-size: 1.2rem !important; }
        
        /* 側邊欄在手機上預設收合時的按鈕調整 */
        [data-testid="stSidebarCollapsedControl"] {
            top: 0.5rem !important;
            left: 0.5rem !important;
        }
    }

    /* === 3. 隱藏不必要的 Streamlit 元素 === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* === 4. 側邊欄按鈕終極美化 (統一大小、垂直排列) === */
    div[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
    }
    
    /* 針對側邊欄裡面的按鈕容器 */
    div[data-testid="stSidebar"] .stButton button {
        width: 100% !important;           /* 強制滿寬 */
        text-align: left !important;      /* 文字靠左 */
        justify-content: flex-start !important;
        border: 1px solid rgba(128,128,128, 0.3) !important;
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
        font-weight: bold !important;
        margin-bottom: 4px !important;    /* 統一間距 */
        height: auto !important;          /* 高度自適應 */
        min-height: 48px !important;      /* 設定最小高度 */
        padding: 10px 15px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }

    div[data-testid="stSidebar"] .stButton button:hover {
        border-color: #FF4B4B !important;
        color: #FF4B4B !important;
        background-color: rgba(255, 75, 75, 0.05) !important;
        transform: translateX(4px);       /* 滑鼠移上去微微右移 */
    }

    /* 側邊欄標題裝飾 */
    .sidebar-section-header {
        font-size: 1.1rem;
        font-weight: 900;
        color: var(--text-color);
        margin-top: 15px;
        margin-bottom: 10px;
        padding-left: 8px;
        border-left: 4px solid #FF4B4B;
        opacity: 0.9;
    }
    
    .sidebar-label {
        font-size: 0.95rem;
        font-weight: bold;
        color: var(--text-color);
        margin-bottom: 2px;
        opacity: 0.8;
    }

    /* === 5. 卡片與列表設計 (深色模式相容) === */
    .topic-container {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        margin-bottom: 16px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        overflow: hidden; /* 防止內容溢出圓角 */
    }
    
    .topic-header {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 12px 15px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .record-row {
        padding: 15px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        line-height: 1.6;
    }

    /* 清單項目 (保養/點檢用) */
    .list-item {
        padding: 12px 15px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        display: flex;
        align-items: flex-start;
        transition: background-color 0.2s;
    }
    .list-item:hover {
        background-color: rgba(128, 128, 128, 0.05);
    }
    .list-icon {
        font-size: 1.2rem;
        margin-right: 12px;
        min-width: 25px;
        text-align: center;
        margin-top: -2px; /* 微調圖示位置 */
    }
    .list-text {
        font-size: 1.05rem;
        word-break: break-word; /* 關鍵：手機上文字自動換行 */
    }

    /* === 6. 顏色定義 (支援深淺模式自動切換) === */
    /* 預設 (淺色模式) */
    .text-red { color: #E53E3E; }
    .text-green { color: #2F855A; }
    .text-normal { color: inherit; }
    
    /* 深色模式覆寫 */
    @media (prefers-color-scheme: dark) {
        .text-red { color: #FC8181; }
        .text-green { color: #68D391; }
    }
    
    /* AI 精選高亮 */
    .highlight-record {
        background-color: rgba(255, 75, 75, 0.08) !important;
        border-left: 5px solid #FF4B4B !important;
    }
    
    /* 標籤 Badge */
    .badge {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 12px;
        background: rgba(128, 128, 128, 0.2);
        color: var(--text-color);
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 資料處理 (顏色邏輯 + 點檢整合)
# ---------------------------------------------------------
HAS_AI = False
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
INSPECT_COLS = ['項目各部', '各部細項']

# === 保養料件顏色規則 ===
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
    # 移除 "保養" 二字並轉大寫，確保對應 key
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
    return text.replace("**", "").replace("\n", " ").strip()

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

# --- 資料讀取函數 ---

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
        
        # 資料清洗與填補
        df.replace("", float("NaN"), inplace=True)
        df['保養類型'] = df['保養類型'].ffill()
        df['型號'] = df['型號'].ffill()
        
        # 統一轉大寫並去除空白，解決 500k/500K 重複問題
        df['保養類型'] = df['保養類型'].astype(str).str.upper().str.strip()
        
        df = df.dropna(subset=['更換料件'])
        df.fillna("", inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=MAINTAIN_COLS)

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
# 3. 頁面控制
# ---------------------------------------------------------
def set_view(view_name):
    st.session_state['active_view'] = view_name
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
    # 強制置頂 (JavaScript)
    if st.session_state.get('scroll_to_top'):
        components.html(
            """<script>
            setTimeout(function() {
                var section = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                if (section) { section.scrollTo({top: 0, behavior: 'smooth'}); }
            }, 100);
            </script>""", 
            height=0
        )
        st.session_state['scroll_to_top'] = False

    df_repair = load_repair_data()
    df_maintain = load_maintain_data()
    df_inspect = load_inspect_data()
    
    vectorizer, tfidf_matrix = build_search_engine(df_repair['search_content'])
    
    all_repair_models = sorted(list(set(df_repair['設備型號'].astype(str).tolist()))) if not df_repair.empty else []
    maintain_intervals = sorted(list(set(df_maintain['保養類型'].astype(str).tolist()))) if not df_maintain.empty else []
    inspect_items = sorted(list(set(df_inspect['項目各部'].astype(str).tolist()))) if not df_inspect.empty else []

    # === 側邊欄設計 (統一垂直排列) ===
    with st.sidebar:
        st.markdown('<div class="sidebar-section-header">🎛️ 中控台</div>', unsafe_allow_html=True)
        
        # 統一按鈕
        if st.button("🧠 AI 智能診斷"): set_view("ai_search")
        if st.button("📊 全域戰情室"): set_view("dashboard")
        
        # 新增與修改 (專屬頁面)
        if st.button("➕ 新增/編輯紀錄"):
            st.session_state['edit_mode'] = False 
            st.session_state['edit_data'] = None
            set_view("add_edit_repair")
            st.rerun()
            
        st.markdown("---")
        
        # === 1. 設備目錄 ===
        with st.expander("📂 設備維修目錄", expanded=False):
            st.markdown('<span class="sidebar-label">選擇機型查閱履歷</span>', unsafe_allow_html=True)
            selected_model_dd = st.selectbox("選擇機型", ["請選擇..."] + all_repair_models, index=0, key="sb_repair", label_visibility="collapsed")
            if selected_model_dd != "請選擇...":
                if st.button("🔍 查詢履歷"):
                    st.session_state['selected_model'] = selected_model_dd
                    st.session_state['target_category'] = "全部顯示"
                    st.session_state['target_topic'] = "全部顯示"
                    set_view("repair_log")
                    st.rerun()

        # === 2. 保養目錄 ===
        with st.expander("🛠️ 定期保養目錄", expanded=False):
            st.markdown('<span class="sidebar-label">1. 選擇保養里程</span>', unsafe_allow_html=True)
            sel_interval = st.selectbox("選擇保養里程", ["請選擇..."] + maintain_intervals, key="sb_m_int", label_visibility="collapsed")
            
            m_models = []
            if sel_interval != "請選擇...":
                m_models = sorted(list(set(df_maintain[df_maintain['保養類型'] == sel_interval]['型號'].astype(str).tolist())))
            
            st.markdown('<span class="sidebar-label">2. 選擇機型</span>', unsafe_allow_html=True)
            sel_m_model = st.selectbox("選擇機型", ["請選擇..."] + m_models, key="sb_m_mod", disabled=(sel_interval == "請選擇..."), label_visibility="collapsed")
            
            if sel_m_model != "請選擇...":
                if st.button("📋 查看料件"):
                    st.session_state['selected_maintain_interval'] = sel_interval
                    st.session_state['selected_maintain_model'] = sel_m_model
                    set_view("maintenance_log")
                    st.rerun()

        # === 3. 點檢目錄 ===
        with st.expander("📋 點檢基準目錄", expanded=False):
            st.markdown('<span class="sidebar-label">選擇項目各部</span>', unsafe_allow_html=True)
            sel_inspect_item = st.selectbox("選擇項目", ["請選擇..."] + inspect_items, key="sb_inspect", label_visibility="collapsed")
            if sel_inspect_item != "請選擇...":
                if st.button("👁️ 查看細節"):
                    st.session_state['selected_inspect_item'] = sel_inspect_item
                    set_view("inspect_log")
                    st.rerun()

    # ==========================
    # 主畫面 View 路由
    # ==========================

    # 1. AI 搜尋
    if st.session_state['active_view'] == "ai_search":
        st.markdown('<h1>🧠 設備維修智慧搜尋 <span style="font-size:1rem; color:gray;">(自動遞補最佳建議)</span></h1>', unsafe_allow_html=True)
        query = st.text_input("💬 故障描述", placeholder="試試看輸入：馬達異音、皮帶斷裂...", value=st.session_state['search_input_val'])
        if query != st.session_state['search_input_val']:
            st.session_state['search_input_val'] = query
            st.rerun()
        if query:
            with st.spinner("⚡ AI 深度檢索..."):
                results, summary, ext = super_smart_search(query, df_repair, vectorizer, tfidf_matrix)
            st.markdown(summary, unsafe_allow_html=True)
            if ext: st.link_button("🌐 外部搜尋 (Google)", ext, type="secondary")
            if not results.empty:
                st.markdown("### 📋 內部相似案例")
                for i, row in results.iterrows():
                    st.markdown(f"""
                    <div class="topic-container" style="padding:15px; border-left:5px solid #3182CE;">
                        <div style="display:flex; justify-content:space-between;">
                            <h3>🔧 {row['主題(事件簡述)']}</h3>
                            <span style="font-size:0.8rem; background:rgba(128,128,128,0.2); padding:2px 8px; border-radius:10px;">{row['設備型號']}</span>
                        </div>
                        <div style="margin-top:8px;">
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
        if not df_repair.empty:
            with st.expander("⚙️ 篩選", expanded=True):
                sel_mods = st.multiselect("機型篩選", all_repair_models, default=all_repair_models)
                df_chart = df_repair[df_repair['設備型號'].isin(sel_mods)]
            if not df_chart.empty:
                st.markdown("### 🟠 設備異常總覽")
                fig = px.treemap(df_chart, path=[px.Constant("全廠"), '設備型號', '大標', '主題(事件簡述)'], color='大標')
                fig.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=500)
                st.plotly_chart(fig, use_container_width=True)

    # 3. 維修履歷
    elif st.session_state['active_view'] == "repair_log":
        t_model = st.session_state['selected_model']
        t_id = st.session_state['target_case_id']
        t_cat = st.session_state.get('target_category', "全部顯示")
        
        st.markdown(f'<h1>📄 {t_model} 維修履歷</h1>', unsafe_allow_html=True)
        
        df_m = df_repair[df_repair['設備型號'] == t_model]
        cats = ["全部顯示"] + sorted(list(set(df_m['大標'].tolist())))
        idx = cats.index(t_cat) if t_cat in cats else 0
        sel_cat = st.radio("大標", cats, index=idx, horizontal=True)
        st.session_state['target_category'] = sel_cat
        
        df_show = df_m if sel_cat == "全部顯示" else df_m[df_m['大標'] == sel_cat]
        
        if t_id is not None: # 將目標置頂
            t_row = df_show[df_show['original_id'] == t_id]
            o_rows = df_show[df_show['original_id'] != t_id]
            df_show = pd.concat([t_row, o_rows])

        grouped = df_show.groupby('主題(事件簡述)', sort=False)
        for topic, group in grouped:
            st.markdown(f"""<div class="topic-container"><div class="topic-header"><span>📌 {topic}</span><span class="badge">{len(group)}</span></div>""", unsafe_allow_html=True)
            for i, row in group.iterrows():
                is_target = (row['original_id'] == t_id)
                hl_class = "highlight-record" if is_target else ""
                icon = "✅ [AI精選]" if is_target else ""
                with st.container():
                    c1, c2 = st.columns([0.9, 0.1])
                    with c1:
                        st.markdown(f"""
                        <div class="record-row {hl_class}" style="border:none;">
                            <div style="color:#ff4b4b; margin-bottom:5px;">{icon}</div>
                            <b>🔴 原因：</b>{row['原因(異常查找、分析)']}<br>
                            <b>🟢 對策：</b>{row['處置、應對']}<br>
                            <span style="font-size:0.9em; opacity:0.8;">驗證：{row['驗證是否排除(驗證作法)']}</span>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        st.write("")
                        if st.button("✏️", key=f"ed_{row['original_id']}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['edit_data'] = row.to_dict()
                            set_view("add_edit_repair")
                            st.rerun()
                st.markdown("<hr style='margin:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 4. 保養料件 (顏色)
    elif st.session_state['active_view'] == "maintenance_log":
        inv = st.session_state['selected_maintain_interval']
        mod = st.session_state['selected_maintain_model']
        st.markdown(f'<h1>🛠️ 保養料件清單</h1>', unsafe_allow_html=True)
        st.info(f"當前：**{inv}** - **{mod}**")
        
        df_show = df_maintain[(df_maintain['保養類型'] == inv) & (df_maintain['型號'] == mod)]
        
        if df_show.empty:
            st.warning("無資料")
        else:
            parts = df_show['更換料件'].tolist()
            st.markdown('<div class="topic-container" style="padding:5px;">', unsafe_allow_html=True)
            for p in parts:
                for item in p.split('\n'):
                    it = item.strip()
                    if it:
                        cls, icon = get_part_color_class(it, mod, inv)
                        st.markdown(f"""<div class="list-item"><span class="list-icon">{icon}</span><span class="list-text {cls}">{it}</span></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("⬅️ 返回"): set_view("ai_search"); st.rerun()

    # 5. 點檢 (新)
    elif st.session_state['active_view'] == "inspect_log":
        item = st.session_state['selected_inspect_item']
        st.markdown(f'<h1>📋 {item} 點檢細節</h1>', unsafe_allow_html=True)
        df_show = df_inspect[df_inspect['項目各部'] == item]
        if df_show.empty:
            st.warning("無資料")
        else:
            details = df_show['各部細項'].tolist()
            st.markdown('<div class="topic-container" style="padding:5px;">', unsafe_allow_html=True)
            for d in details:
                for line in str(d).split('\n'):
                    ln = line.strip()
                    if ln:
                        st.markdown(f"""<div class="list-item"><span class="list-icon">🔍</span><span class="list-text text-normal">{ln}</span></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("⬅️ 返回"): set_view("ai_search"); st.rerun()

    # 6. 新增/編輯
    elif st.session_state['active_view'] == "add_edit_repair":
        is_edit = st.session_state['edit_mode']
        st.markdown(f"<h1>{'📝 編輯' if is_edit else '➕ 新增'}維修紀錄</h1>", unsafe_allow_html=True)
        
        default = st.session_state['edit_data'] if is_edit else {}
        ex_models = sorted(list(set(df_repair['設備型號'].astype(str).tolist())))
        ex_cats = sorted(list(set(df_repair['大標'].astype(str).tolist())))
        
        c1, c2 = st.columns(2)
        with c1:
            curr = default.get('設備型號', ex_models[0] if ex_models else "")
            idx = ex_models.index(curr) if curr in ex_models else len(ex_models)
            sel_mod = st.selectbox("設備型號", ex_models + ["➕ 手動"], index=idx)
            fin_mod = st.text_input("輸入型號", value=curr if curr not in ex_models else "") if sel_mod == "➕ 手動" else sel_mod
        with c2:
            curr_c = default.get('大標', ex_cats[0] if ex_cats else "")
            idx_c = ex_cats.index(curr_c) if curr_c in ex_cats else len(ex_cats)
            sel_cat = st.selectbox("大標", ex_cats + ["➕ 手動"], index=idx_c)
            fin_cat = st.text_input("輸入分類", value=curr_c if curr_c not in ex_cats else "") if sel_cat == "➕ 手動" else sel_cat

        with st.form("edit_form"):
            topic = st.text_area("主題 (必填)", value=default.get('主題(事件簡述)', ""))
            c_cause, c_sol = st.columns(2)
            cause = c_cause.text_area("原因", value=default.get('原因(異常查找、分析)', ""), height=150)
            sol = c_sol.text_area("對策", value=default.get('處置、應對', ""), height=150)
            ver = st.text_area("驗證", value=default.get('驗證是否排除(驗證作法)', ""))
            rem = st.text_area("備註", value=default.get('備註(建議事項及補充事項)', ""))
            
            st.markdown("---")
            b1, b2, b3 = st.columns([1,1,2])
            if b1.form_submit_button("💾 儲存", type="primary"):
                if not fin_mod or not topic:
                    st.error("型號與主題為必填")
                else:
                    rec = {
                        '設備型號': fin_mod, '大標': fin_cat, '主題(事件簡述)': topic,
                        '原因(異常查找、分析)': cause, '處置、應對': sol,
                        '驗證是否排除(驗證作法)': ver, '備註(建議事項及補充事項)': rem
                    }
                    if is_edit:
                        t_idx = default['original_id']
                        for k, v in rec.items(): df_repair.at[t_idx, k] = v
                    else:
                        df_repair = pd.concat([df_repair, pd.DataFrame([rec])], ignore_index=True)
                    
                    if save_repair_data(df_repair):
                        st.success("成功！"); time.sleep(1)
                        st.session_state['selected_model'] = fin_mod
                        set_view("repair_log"); st.rerun()
            
            if b2.form_submit_button("❌ 取消"):
                set_view("repair_log" if is_edit else "ai_search"); st.rerun()
                
            if is_edit and st.checkbox("🗑️ 刪除此紀錄"):
                if st.form_submit_button("確認刪除"):
                    delete_repair_data(default['original_id'])
                    st.success("已刪除"); time.sleep(1)
                    set_view("repair_log"); st.rerun()

if __name__ == "__main__":
    main()
