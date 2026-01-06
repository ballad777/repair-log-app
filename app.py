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
# 1. 核心設定 & CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="服務報告履歷系統",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 Session State
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = "tab_ai"
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = None
if 'target_case_id' not in st.session_state:
    st.session_state['target_case_id'] = None
if 'target_category' not in st.session_state:
    st.session_state['target_category'] = "全部顯示"
if 'target_topic' not in st.session_state:
    st.session_state['target_topic'] = "全部顯示"
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
if 'edit_data' not in st.session_state:
    st.session_state['edit_data'] = None
if 'saved_search_query' not in st.session_state:
    st.session_state['saved_search_query'] = ""
if 'scroll_to_top' not in st.session_state:
    st.session_state['scroll_to_top'] = False

# CSS 設定
st.markdown("""
<style>
    /* 全域字體：全部加粗 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
        font-weight: bold !important;
    }
    
    /* === 內容區塊滿版化 === */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100% !important;
    }
    
    /* 隱藏原生多餘選單 */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;}

    /* === 側邊欄按鈕 === */
    div[data-testid="stSidebar"] button {
        width: 100%;
        text-align: left;
        background-color: transparent;
        border: 1px solid #4A5568;
        margin-bottom: 5px;
        color: var(--text-color);
        font-weight: bold;
    }
    div[data-testid="stSidebar"] button:hover {
        background-color: #2D3748;
        color: white;
    }
    
    /* === 目錄式按鈕 === */
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

    /* === 卡片樣式 === */
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
    .record-row:last-child {
        border-bottom: none;
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 資料處理
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

REQUIRED_COLUMNS = ['設備型號', '大標', '主題(事件簡述)', '原因(異常查找、分析)', '處置、應對', '驗證是否排除(驗證作法)', '備註(建議事項及補充事項)']
SYNONYMS = {
    "聲音": "異音 噪音 吵雜 聲響", "怪聲": "異音 磨損",
    "不動": "卡死 異常 停止 無法運作失效", "壞掉": "異常 故障 損壞",
    "溫度": "過熱 發燙 高溫", "漏水": "洩漏 滲水",
    "轉速": "速度 變慢", "sensor": "感應器 光電",
    "馬達": "motor", "皮帶": "斷裂 磨損",
    "飛板": "fly board 驅動板", 
}

def clean_text(text):
    if not isinstance(text, str): return str(text)
    text = text.replace("**", "")
    text = text.replace("\n", " ").strip()
    return text

def expand_query(query):
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
def load_data():
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheet_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: return pd.DataFrame(columns=REQUIRED_COLUMNS)
        
        for col in REQUIRED_COLUMNS:
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
        st.error(f"連線錯誤: {e}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

def save_data(df):
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheet_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        cols_to_save = [c for c in df.columns if c in REQUIRED_COLUMNS]
        df_save = df[cols_to_save]
        data_to_write = [df_save.columns.values.tolist()] + df_save.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_write)
        load_data.clear()
        return True
    except Exception as e:
        st.error(f"存檔失敗: {e}")
        return False

def delete_data(index_to_delete):
    try:
        client = get_google_sheet_connection()
        sheet_url = st.secrets["sheet_url"]
        sh = client.open_by_url(sheet_url)
        worksheet = sh.get_worksheet(0)
        worksheet.delete_rows(index_to_delete + 2)
        load_data.clear()
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
        
        if best_row is None:
            best_row = results.iloc[0]

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
# 3. 頁面控制與表單
# ---------------------------------------------------------
def jump_to_case(model_name, case_id, category, topic):
    st.session_state['active_tab'] = "tab_catalog"
    st.session_state['selected_model'] = model_name
    st.session_state['target_case_id'] = case_id 
    st.session_state['target_category'] = category
    st.session_state['target_topic'] = topic

def set_tab(tab_name):
    st.session_state['active_tab'] = tab_name
    st.session_state['target_case_id'] = None

def set_model(model_name):
    st.session_state['active_tab'] = "tab_catalog"
    st.session_state['selected_model'] = model_name
    st.session_state['target_case_id'] = None
    st.session_state['target_category'] = "全部顯示"
    st.session_state['target_topic'] = "全部顯示"

def render_edit_form(df):
    # ★ 強制置頂 JS (增加延遲確保執行) ★
    if st.session_state.get('scroll_to_top'):
        js = """
        <script>
            setTimeout(function() {
                var section = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                if (section) { 
                    section.scrollTo({top: 0, behavior: 'smooth'}); 
                }
            }, 100); // 延遲100ms確保DOM已加載
        </script>
        """
        components.html(js, height=0)
        st.session_state['scroll_to_top'] = False

    if st.session_state['edit_mode']:
        is_edit = st.session_state['edit_data'] is not None
        form_title = "📝 編輯紀錄" if is_edit else "➕ 新增紀錄"
        
        existing_models = sorted(list(set(df['設備型號'].tolist()))) if not df.empty else []
        existing_cats = sorted(list(set(df['大標'].tolist()))) if not df.empty else []
        
        model_options = existing_models + ["➕ 手動輸入"]
        cat_options = existing_cats + ["➕ 手動輸入"]

        with st.expander(form_title, expanded=True):
            # === 1. 互動式選單 (移出 st.form) ===
            default_data = st.session_state['edit_data'] if is_edit else {}
            
            st.markdown("##### 📍 設備型號")
            curr_model = default_data.get('設備型號', existing_models[0] if existing_models else "")
            
            if curr_model in existing_models:
                idx_model = existing_models.index(curr_model)
            else:
                idx_model = len(model_options) - 1

            sel_model = st.radio("設備型號選擇", model_options, index=idx_model, horizontal=True, label_visibility="collapsed", key="radio_model_select")
            
            if sel_model == "➕ 手動輸入":
                default_text = curr_model if curr_model not in existing_models else ""
                new_model = st.text_input("輸入新設備型號", value=default_text, key="input_model_manual")
            else:
                new_model = sel_model
            
            st.write("")
            
            st.markdown("##### 🏷️ 分類 (大標)")
            curr_cat = default_data.get('大標', existing_cats[0] if existing_cats else "")
            
            if curr_cat in existing_cats:
                idx_cat = existing_cats.index(curr_cat)
            else:
                idx_cat = len(cat_options) - 1

            sel_cat = st.radio("大標選擇", cat_options, index=idx_cat, horizontal=True, label_visibility="collapsed", key="radio_cat_select")
            
            if sel_cat == "➕ 手動輸入":
                default_cat_text = curr_cat if curr_cat not in existing_cats else ""
                new_cat = st.text_input("輸入新分類", value=default_cat_text, key="input_cat_manual")
            else:
                new_cat = sel_cat

            st.write("")

            # === 2. 靜態資料表單 (防止Enter誤觸，改用 Text Area) ===
            with st.form("data_entry_form"):
                # 將所有可能需要打字的欄位都改為 text_area
                # 這樣按 Enter 變換行，不會送出表單
                new_topic = st.text_area("📝 主題 (事件簡述 - 必填)", value=default_data.get('主題(事件簡述)', ""), height=68)
                
                col_cause, col_sol = st.columns(2)
                with col_cause:
                    new_cause = st.text_area("🔴 原因 (異常查找、分析)", value=default_data.get('原因(異常查找、分析)', ""), height=150)
                with col_sol:
                    new_sol = st.text_area("🟢 處置、應對", value=default_data.get('處置、應對', ""), height=150)
                
                col_ver, col_rem = st.columns(2)
                with col_ver:
                    new_ver = st.text_area("驗證是否排除", value=default_data.get('驗證是否排除(驗證作法)', ""), height=68)
                with col_rem:
                    new_rem = st.text_area("備註", value=default_data.get('備註(建議事項及補充事項)', ""), height=68)
                
                st.markdown("---")
                c_submit, c_space, c_del = st.columns([2, 4, 1])
                with c_submit:
                    submitted = st.form_submit_button("💾 確認儲存", type="primary", use_container_width=True)
                
                delete_check = False
                if is_edit:
                    with c_del:
                        delete_check = st.checkbox("🗑️ 刪除", key="del_check")

                if submitted:
                    if is_edit and delete_check:
                        st.toast("🗑️ 正在刪除...")
                        if delete_data(default_data['original_id']):
                            st.success("已刪除！")
                            st.session_state['edit_mode'] = False
                            st.session_state['edit_data'] = None
                            time.sleep(1)
                            st.rerun()
                    elif not new_model or not new_topic:
                        st.error("⚠️ 「設備型號」與「主題」為必填欄位！")
                    else:
                        new_record = {
                            '設備型號': new_model,
                            '大標': new_cat,
                            '主題(事件簡述)': new_topic,
                            '原因(異常查找、分析)': new_cause,
                            '處置、應對': new_sol,
                            '驗證是否排除(驗證作法)': new_ver,
                            '備註(建議事項及補充事項)': new_rem
                        }
                        
                        if is_edit:
                            target_idx = default_data['original_id']
                            for key, val in new_record.items(): df.at[target_idx, key] = val
                            st.toast("✅ 更新成功！")
                        else:
                            new_row_df = pd.DataFrame([new_record])
                            df = pd.concat([df, new_row_df], ignore_index=True)
                            st.toast("✅ 新增成功！")
                        
                        if save_data(df):
                            st.session_state['edit_mode'] = False
                            st.session_state['edit_data'] = None
                            time.sleep(1)
                            st.rerun()

        if st.button("❌ 關閉編輯視窗", type="secondary"):
            st.session_state['edit_mode'] = False
            st.session_state['edit_data'] = None
            st.rerun()
        st.divider()

# ---------------------------------------------------------
# 4. 主程式執行
# ---------------------------------------------------------
def main():
    df = load_data()
    render_edit_form(df)
    
    vectorizer, tfidf_matrix = build_search_engine(df['search_content'])
    all_models = sorted(list(set(df['設備型號'].astype(str).tolist()))) if not df.empty else []

    with st.sidebar:
        st.header("🎛️ 中控台")
        if st.button("🧠 AI 智能診斷", use_container_width=True): set_tab("tab_ai")
        if st.button("📊 全域戰情室", use_container_width=True): set_tab("tab_chart")
        st.markdown("---")
        if st.button("➕ 新增紀錄", type="primary", use_container_width=True):
            st.session_state['edit_mode'] = True
            st.session_state['edit_data'] = None
            st.session_state['scroll_to_top'] = True 
            st.rerun()
            
        st.caption("📂 設備目錄")
        with st.container(height=450):
            for model in all_models:
                prefix = "📍" if st.session_state.get('selected_model') == model else "📄"
                if st.button(f"{prefix} {model}", key=f"nav_{model}"):
                    set_model(model)
                    st.rerun()

    # --- AI 診斷 Tab ---
    if st.session_state['active_tab'] == "tab_ai":
        st.markdown('<h1>🧠 設備維修智慧搜尋 <span style="font-size:1rem; color:gray;">(自動遞補最佳建議)</span></h1>', unsafe_allow_html=True)
        
        query = st.text_input("💬 故障描述", placeholder="試試看輸入：馬達異音、皮帶斷裂...", value=st.session_state['saved_search_query'])
        st.session_state['saved_search_query'] = query

        if query:
            with st.spinner("⚡ AI 深度檢索 & 外部資源比對中..."):
                results, summary_html, ext_link = super_smart_search(query, df, vectorizer, tfidf_matrix)
            
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
                        jump_to_case(row['設備型號'], row['original_id'], row['大標'], row['主題(事件簡述)'])
                        st.rerun()

    # --- 全域戰情室 Tab ---
    elif st.session_state['active_tab'] == "tab_chart":
        st.markdown('<h1>📊 全域戰情室</h1>', unsafe_allow_html=True)
        if df.empty:
            st.warning("目前無資料")
        else:
            with st.expander("⚙️ 圖表資料篩選", expanded=True):
                selected_models_chart = st.multiselect(
                    "選擇分析機型 (預設全選，可點擊 X 移除)", 
                    all_models, 
                    default=all_models
                )
                df_chart = df[df['設備型號'].isin(selected_models_chart)]

            st.divider()
            
            if not df_chart.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("案件數", len(df_chart))
                m2.metric("機型數", df_chart['設備型號'].nunique())
                m3.metric("分類數", df_chart['大標'].nunique())
                
                COLOR_PALETTE = ['#334155', '#0F766E', '#1E40AF', '#3730A3', '#166534', '#9A3412']

                st.markdown("### 🟠 設備異常總覽 (矩形圖)")
                
                df_treemap = df_chart.copy()
                def split_text(text):
                    if not isinstance(text, str): return str(text)
                    return "<br>".join([text[i:i+6] for i in range(0, len(text), 6)])
                
                df_treemap['display_text'] = df_treemap['主題(事件簡述)'].apply(split_text)

                fig_tree = px.treemap(
                    df_treemap, 
                    path=[px.Constant("全廠"), '設備型號', '大標', 'display_text'], 
                    color='大標', 
                    color_discrete_sequence=COLOR_PALETTE
                )
                
                fig_tree.update_traces(
                    textinfo="label+value", 
                    textposition="middle center",
                    textfont=dict(size=16, family="Microsoft JhengHei", color="white", weight='bold'),
                    hovertemplate='<b>%{label}</b><br>次數: %{value}<extra></extra>',
                    marker=dict(line=dict(width=1, color='white'))
                )
                fig_tree.update_layout(
                    margin=dict(t=50, l=10, r=10, b=10),
                    height=600,
                    uniformtext=dict(minsize=10, mode=False)
                )
                st.plotly_chart(fig_tree, use_container_width=True)
                
                st.divider()
                
                # 這裡更換了 emoji
                st.markdown("### 🔥 Top 20 高頻異常原因")
                top_issues = df_chart['主題(事件簡述)'].value_counts().head(20).reset_index()
                top_issues.columns = ['主題', '次數']
                
                fig_bar = px.bar(
                    top_issues, x='次數', y='主題', orientation='h', text='次數',
                    color='次數', color_continuous_scale='Greys'
                )
                fig_bar.update_traces(
                    textfont=dict(weight='bold', size=14),
                    marker_line_color='rgb(8,48,107)', marker_line_width=1, opacity=0.9
                )
                fig_bar.update_layout(
                    yaxis=dict(autorange="reversed", tickfont=dict(weight='bold')),
                    xaxis=dict(title="發生次數", tickfont=dict(weight='bold')),
                    height=600,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    # --- 設備履歷目錄 Tab ---
    elif st.session_state['active_tab'] == "tab_catalog":
        target_model = st.session_state['selected_model']
        target_id = st.session_state['target_case_id']
        target_cat = st.session_state.get('target_category', "全部顯示")
        target_topic = st.session_state.get('target_topic', "全部顯示")
        
        if not target_model:
            st.warning("⚠️ 請從左側選擇機型")
            st.stop()
            
        st.markdown(f'<h1>📄 {target_model} 完整履歷</h1>', unsafe_allow_html=True)
        df_model = df[df['設備型號'] == target_model]
        
        st.markdown("### 1️⃣ 選擇分類")
        all_cats = sorted(list(set(df_model['大標'].tolist())))
        cat_search = st.text_input("🔍 篩選分類", placeholder="輸入關鍵字過濾分類...", key="cat_search")
        if cat_search:
            filtered_cats = [c for c in all_cats if cat_search.lower() in c.lower()]
        else:
            filtered_cats = all_cats
            
        cats_display = ["全部顯示"] + filtered_cats
        
        current_idx = 0
        if target_cat in cats_display:
            current_idx = cats_display.index(target_cat)
            
        sel_cat = st.radio("大標", cats_display, index=current_idx, horizontal=True, label_visibility="collapsed", key="cat_filter")
        st.session_state['target_category'] = sel_cat
        df_l1 = df_model if sel_cat == "全部顯示" else df_model[df_model['大標'] == sel_cat]

        if not df_l1.empty:
            st.divider()
            st.markdown("### 2️⃣ 選擇主題")
            all_topics = sorted(list(set(df_l1['主題(事件簡述)'].tolist())))
            
            topic_search = st.text_input("🔍 篩選主題", placeholder="輸入關鍵字過濾主題...", key="topic_search")
            if topic_search:
                filtered_topics = [t for t in all_topics if topic_search.lower() in t.lower()]
            else:
                filtered_topics = all_topics
                
            topics_display = ["全部顯示"] + filtered_topics
            
            topic_idx = 0
            if target_topic in topics_display:
                topic_idx = topics_display.index(target_topic)
                
            sel_topic = st.radio("主題", topics_display, index=topic_idx, horizontal=True, label_visibility="collapsed", key="topic_filter")
            st.session_state['target_topic'] = sel_topic
            df_final = df_l1 if sel_topic == "全部顯示" else df_l1[df_l1['主題(事件簡述)'] == sel_topic]
        else:
            df_final = pd.DataFrame()
            
        st.divider()
        if df_final.empty:
            st.info("此分類下無資料")
        else:
            grouped = df_final.groupby('主題(事件簡述)')
            group_keys = sorted(grouped.groups.keys())
            
            target_group_key = None
            if target_id is not None:
                row = df_final[df_final['original_id'] == target_id]
                if not row.empty: target_group_key = row['主題(事件簡述)'].iloc[0]
            if target_group_key and target_group_key in group_keys:
                group_keys.remove(target_group_key)
                group_keys.insert(0, target_group_key)

            for topic_name in group_keys:
                group_data = grouped.get_group(topic_name)
                st.markdown(f"""
                <div class="topic-container">
                    <div class="topic-header">
                        <span>📌 {topic_name}</span>
                        <span class="badge">{len(group_data)} 筆紀錄</span>
                    </div>""", unsafe_allow_html=True)
                
                for idx, row in group_data.iterrows():
                    is_target = (row['original_id'] == target_id)
                    row_class = "highlight-record" if is_target else ""
                    target_icon = "✅ [AI精選]" if is_target else ""
                    
                    with st.container():
                        c_content, c_edit = st.columns([0.92, 0.08])
                        with c_content:
                            st.markdown(f"""
                            <div class="record-row {row_class}" style="border-bottom:none; padding-bottom:5px;">
                                <div style="font-weight:bold; color:#ff4b4b; margin-bottom:5px;">{target_icon}</div>
                                <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                                    <div style="flex: 2; min-width: 300px;">
                                        <p><strong style="color:#c53030;">🔴 原因：</strong> {clean_text(row['原因(異常查找、分析)'])}</p>
                                        <p><strong style="color:#2f855a;">🟢 對策：</strong> {clean_text(row['處置、應對'])}</p>
                                    </div>
                                    <div style="flex: 1; min-width: 200px; border-left: 3px solid rgba(128,128,128,0.2); padding-left: 15px; font-size: 0.9em; opacity:0.8;">
                                        <p><b>驗證：</b> {row['驗證是否排除(驗證作法)']}</p>
                                        <p><b>備註：</b> {row['備註(建議事項及補充事項)']}</p>
                                    </div>
                                </div>
                            </div>""", unsafe_allow_html=True)
                        with c_edit:
                            st.write(""); st.write("")
                            if st.button("✏️", key=f"edit_btn_{row['original_id']}"):
                                st.session_state['edit_mode'] = True
                                st.session_state['edit_data'] = row.to_dict()
                                st.session_state['scroll_to_top'] = True 
                                st.rerun()
                    st.markdown("<hr style='margin:0; border:0; border-top:1px solid rgba(128,128,128,0.1);'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
