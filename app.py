import streamlit as st
import time
import json
import base64
from datetime import datetime
from firebase_admin import initialize_app, credentials, firestore

# --- 載入 Firebase 相關套件 ---
try:
    firebase_config_json = json.loads(st.secrets["__firebase_config"])
    cred = credentials.Certificate(firebase_config_json)
    initialize_app(cred)
    db = firestore.client()

    USER_ID = "stream_user_123"
except Exception as e:
    st.sidebar.warning(f"🚨 Firebase 初始化失敗 ({e.__class__.__name__}). 使用模擬模式。")
    db = None
    USER_ID = "local_user_456"

APP_ID = st.secrets["__app_id"] if "__app_id" in st.secrets else "default-app-id"

# --- 載入自訂 CSS 樣式 ---
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠️ 找不到 style.css 檔案。")

load_css("style.css")

# --- App 基礎設定與常數 ---
st.set_page_config(
    page_title="MagicTales",
    page_icon="🦄",
    layout="centered",
    initial_sidebar_state="expanded"
)

WORD_COUNT_MAP = {
    "3 分鐘 (300 字)": 300,
    "5 分鐘 (500 字)": 500,
    "8 分鐘 (800 字)": 800,
    "12 分鐘 (1200 字)": 1200,
}

CEFR_HINTS = {
    "A0 (入門)": "基礎詞彙，約 150 字內，適合剛接觸英文的學齡前兒童。",
    "A1 (初級)": "認識簡單日常用語，約 250 字內，適用於小學低年級。",
    "A1+ (初級進階)": "能理解常見短句，約 350 字內，適用於小學中年級。",
    "A2 (基礎)": "能描述簡單背景，約 500 字內，適用於小學高年級。",
    "A2+ (基礎進階)": "能處理簡單交流，約 700 字內，適用於國中預備。",
    "B1 (中級)": "能應對旅行、工作等主題，約 1000 字內。",
    "B2 (中高級)": "能理解複雜文章主要觀點，約 1500 字內。",
}

# --- Session State 初始化 ---
if 'coins' not in st.session_state:
    st.session_state.coins = 100
if 'is_premium' not in st.session_state:
    st.session_state.is_premium = False
if 'library' not in st.session_state:
    st.session_state.library = []
if 'current_story_data' not in st.session_state:
    st.session_state.current_story_data = None
if 'story_generated' not in st.session_state:
    st.session_state.story_generated = False
if 'loading' not in st.session_state:
    st.session_state.loading = False

# --- 生成故事的函數 ---
def call_gemini_story(hero, theme, level, word_count, style, extras):
    """模擬呼叫 Gemini API 生成故事和詞彙"""
    # (您的故事生成邏輯)
    pass  # 請替換為實際的生成邏輯

def call_gemini_tts(story_text):
    """模擬呼叫 Gemini TTS API 生成音頻"""
    # (您的語音合成邏輯)
    pass  # 請替換為實際的語音生成邏輯

# --- 側邊欄 ---
with st.sidebar:
    st.title("🦄 設定與後台")
    st.caption("開發者/數據追蹤區")
    
    premium_switch = st.toggle("啟動 Premium 會員", value=st.session_state.is_premium)
    st.session_state.is_premium = premium_switch
        
    if st.session_state.is_premium:
        st.success("目前狀態：VIP 會員 👑")
    else:
        st.info("目前狀態：免費會員")
        
    st.divider()
    st.metric("持有金幣", st.session_state.coins)
    st.caption(f"App ID: {APP_ID} | User ID: {USER_ID}")

# 主標題
st.header("MagicTales 兒童英語故事屋 📖")

# 建立分頁 (Tabs)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "✨ Story Request", "📚 Library", "🔥 Hot Stories", "🛠️ Tool"])

# ----------------------------------------------------
# --- Tab 1: Home ---
# ----------------------------------------------------
with tab1:
    st.subheader("我的學習進度")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本週閱讀", "3 篇")
    with col2:
        st.metric("連續登入", "5 天", "🔥")
    with col3:
        st.metric("總單字量", "520", "+12%")
        
    st.progress(0.6, text="距離下個獎勵還差 40%")
    st.divider()
    
    # Premium 解鎖的英文
    if st.session_state.is_premium:
        st.write("👑 **Premium 熱門故事**")
        st.image("https://placehold.co/400x150/8a2be2/ffffff?text=VIP+Adventure", caption="只有VIP才能閱讀的獨家主題")

    # 經典故事
    st.write("📚 **經典英文故事**")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.button("Three Little Pigs", use_container_width=True)
    with col_c2:
        st.button("The Lion and Mouse", use_container_width=True)

# ----------------------------------------------------
# --- Tab 2: Story Request ---
# ----------------------------------------------------
with tab2:
    st.subheader("✨ 創建你的專屬故事！")
    
    level = st.selectbox("CEFR 英文程度分級", options=list(CEFR_HINTS.keys()))
    st.markdown(f'<div class="cefr-hint">{CEFR_HINTS[level]}</div>', unsafe_allow_html=True)
    
    with st.container(border=True): 
        st.caption("主角設定與偏好")
        hero_name = st.text_input("主角名字 (必填)", "Leo", key="hero_input")
        pet_name = st.text_input("寵物名字 (可選)", "Rex")
        city_name = st.text_input("居住城市", "London")
    
    if st.session_state.is_premium:
        superpower = st.selectbox("⚡ 選擇超能力 (VIP 專屬)", ["無 (None)", "隱形斗篷 (Invisibility)", "會飛 (Flight)", "噴火 (Fire Breath)"])
    else:
        superpower = st.selectbox("⚡ 選擇超能力 (VIP 專屬)", ["無 (None)"], disabled=True)
        st.caption("🔒 升級 VIP 才能解鎖超能力！")
    
    story_minutes = st.select_slider("故事長度 (閱讀時間)", options=list(WORD_COUNT_MAP.keys()))
    word_count = WORD_COUNT_MAP[story_minutes]

    style = st.selectbox("故事風格", ["溫馨 (Warm)", "冒險 (Adventure)", "搞笑 (Funny)"])
    if st.session_state.is_premium:
        theme = st.selectbox("故事主題 (VIP 可選)", ["上學焦慮 (School Anxiety)", "勇氣 (Courage)", "分享 (Sharing)", "保持專注力 (Focus)"])
    else:
        theme = st.selectbox("故事主題", ["上學第一天 (First Day)", "小動物 (Animals)", "新朋友 (New Friends)"])

    if st.button("✨ 產生故事 & 語音檔", type="primary"):
        if not hero_name:
            st.error("❌ 請輸入主角名字！")
        else:
            extras = {
                "city": city_name, 
                "pet": pet_name, 
                "superpower": superpower
            }
            gemini_result = call_gemini_story(hero_name, theme, level, word_count, style, extras)
            if gemini_result:
                st.session_state.current_story_data = {
                    "title": f"🚀 {hero_name} 的 {theme} 冒險",
                    "text": gemini_result['story'],
                    "vocab": gemini_result['vocab'],
                }
                st.success("✅ 故事和語音檔已生成！")

    if st.session_state.current_story_data:
        data = st.session_state.current_story_data
        st.success("故事生成完成！")
        st.markdown(f"### {data['title']}")
        st.markdown(data['text'])
        st.write(f"**🔑 精選高頻詞：** {', '.join(data['vocab'])}")

# ----------------------------------------------------
# --- Tab 3: Library ---
# ----------------------------------------------------
with tab3:
    st.subheader("📚 我的書櫃")
    search_term = st.text_input("🔎 搜尋故事標題...", "")
    
    filtered_library = [
        book for book in st.session_state.library 
        if search_term.lower() in book.lower()
    ]
    
    if not st.session_state.library:
        st.write("書櫃還是空的，快去產生故事吧！")
    else:
        for book in filtered_library:
            st.info(f"📖 {book}")

# ----------------------------------------------------
# --- Tab 4: Hot Stories ---
# ----------------------------------------------------
with tab4:
    st.subheader("🔥 本週熱門主題")
    st.write("這裡列出熱門主題...")

# ----------------------------------------------------
# --- Tab 5: Tool ---
# ----------------------------------------------------
with tab5:
    st.subheader("🛠️ 數據與工具")
    st.write("這裡可以進行數據記錄...")