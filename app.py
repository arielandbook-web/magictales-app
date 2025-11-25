import streamlit as st
import time
import json
import requests
import random
from datetime import datetime
import io
from gtts import gTTS

# --- 1. App 基礎設定 ---
st.set_page_config(
    page_title="MagicTales",
    page_icon="🦄",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. 載入 Secrets (API Key, APP_ID, Firebase Config) ---
# 將所有 Secrets 讀取放在一起，確保 Streamlit 順利處理
APP_ID = st.secrets.get("__app_id", "default-app-id")

try:
    API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    # 如果找不到 API Key，將其設為空字串，讓 UI 顯示警告
    API_KEY = ""
    st.sidebar.error("⚠️ 未設定 Gemini API Key (請檢查 Streamlit Secrets)")

# 定義最穩定的模型名稱和 API 版本
# 🚨 修正：切換回 v1beta 才能使用 responseMimeType (JSON 結構化輸出)
BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
MODEL_TEXT = "gemini-2.5-flash"

# --- 3. Firebase 初始化 (靜默模式) ---
db = None
USER_ID = "guest_user"

# 確保所有 Firebase 相關的 import 都在 try 區塊內
try:
    from firebase_admin import initialize_app, credentials, firestore, get_app
    
    # 檢查 Firebase App 是否已經初始化
    try:
        get_app()
    except ValueError:
        # 只有在 Streamlit Cloud 環境中才嘗試初始化
        if "__firebase_config" in st.secrets:
            firebase_config = json.loads(st.secrets["__firebase_config"])
            # 使用模擬的憑證
            cred = credentials.Certificate(firebase_config) 
            initialize_app(cred)
    
    # 初始化 Firestore 客戶端
    db = firestore.client()
    USER_ID = "stream_user_123"
    
except Exception as e:
    # 本地運行或缺少配置時，db 保持為 None
    # st.sidebar.warning(f"Firebase Init Error: {e}") # 不顯示給用戶
    db = None

# --- 4. CSS 樣式 ---
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f7f9fc;
    }
    .stApp header {
        background-color: #e0b0ff;
    }
    .stButton>button {
        background-image: linear-gradient(to right, #6a5acd, #a020f0);
        color: white;
        border-radius: 8px;
        border: none;
        transition: transform 0.1s;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    .cefr-hint {
        background-color: #fffacd;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #ffd700;
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 5. 初始化狀態 ---
if 'library' not in st.session_state: st.session_state.library = []
if 'is_premium' not in st.session_state: st.session_state.is_premium = False
if 'current_story' not in st.session_state: st.session_state.current_story = None

# 常數定義
CEFR_HINTS = {
    "A0": "入門：150字內。極簡短句。",
    "A1": "初級：250字內。簡單日常用語。",
    "A1+": "初級進階：350字內。常見句子。",
    "A2": "基礎：500字內。簡單背景描述。",
    "A2+": "基礎進階：700字內。簡單交流。",
    "B1": "中級：1000字內。生活主題。",
    "B2": "中高級：1500字內。抽象概念。"
}
WORD_COUNTS = {"3 分鐘": 300, "5 分鐘": 500, "8 分鐘": 800, "12 分鐘": 1200}

# --- 6. 核心函數 ---
def generate_story_with_gemini(hero, theme, level, word_count, style, extras):
    # 確保 API Key 存在
    if not API_KEY:
        return None

    prompt = (
        f"Write a children's story (English).\n"
        f"Hero: {hero}, Pet: {extras['pet']}, City: {extras['city']}\n"
        f"Theme: {theme}, Style: {style}, Color: {extras['color']}\n"
        f"Level: {level}, Length: {word_count} words.\n"
        f"Superpower: {extras['superpower']}\n"
        f"Output JSON format strictly: {{'story': '...', 'vocab': ['w1', 'w2', 'w3', 'w4', 'w5']}}"
    )

    # 組裝 API 請求 URL，包含 API Key
    url = f"{BASE_API_URL}{MODEL_TEXT}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        # responseMimeType 只能在 v1beta API 中使用
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        # 使用 requests 庫發送 POST 請求
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 檢查 API 狀態碼
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
        
        # 解析 JSON 結果
        result = response.json()
        
        # 提取模型生成的文字內容 (JSON 字符串)
        # 由於我們使用了 responseMimeType，text 應該就是 JSON 字串
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        
        # 將模型返回的 JSON 字符串解析為 Python 字典
        return json.loads(text_content)
        
    except Exception as e:
        # 捕捉所有可能的錯誤，例如 JSON 解析錯誤或連線超時
        st.error(f"連線或解析錯誤: {e}")
        return None

def generate_audio_gtts(text):
    """使用 gTTS 庫將文字轉換為 MP3 格式的音頻。"""
    try:
        # gTTS 語音生成
        tts = gTTS(text=text, lang='en', slow=False)
        # 將音頻數據寫入 BytesIO 物件
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        # 重置指針到開頭，讓 st.audio 可以讀取
        fp.seek(0)
        return fp
    except Exception as e:
        st.warning(f"Audio Generation Error: {e}")
        return None

# --- 7. UI 介面 ---
st.title("MagicTales 兒童英語故事屋 📖")

# 檢查 API Key，如果沒有就顯示警告在主畫面頂部
if not API_KEY:
    st.error("❌ 請設定 API Key 才能生成故事！ (請檢查 Streamlit Secrets 設定)")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "✨ Story Request", "📚 Library", "🔥 Hot", "🛠️ Tool"])

# --- Tab 1: Home ---
with tab1:
    st.subheader("歡迎回來！")
    col1, col2 = st.columns(2)
    with col1: st.metric("本週閱讀", "3 篇")
    with col2: st.metric("閱讀進度", "Level A1")
    st.progress(0.4, text="距離升級還差 60%")
    
    st.markdown("### 🏆 經典故事")
    c1, c2 = st.columns(2)
    c1.button("🐷 Three Little Pigs", use_container_width=True)
    c2.button("🐺 Little Red Riding Hood", use_container_width=True)

    if st.session_state.is_premium:
        st.success("👑 Premium 會員已啟用")
    else:
        st.info("💡 升級 Premium 解鎖更多功能！")

# --- Tab 2: Story Request ---
with tab2:
    st.subheader("✨ 創建專屬故事")
    level_key = st.selectbox("選擇 CEFR 等級", list(CEFR_HINTS.keys()))
    st.markdown(f'<div class="cefr-hint">{CEFR_HINTS[level_key]}</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.caption("主角設定")
        c1, c2 = st.columns(2)
        hero = c1.text_input("主角名字 (英文)", "Leo")
        pet = c2.text_input("寵物名字", "Rex")
        c3, c4 = st.columns(2)
        color = c3.color_picker("喜歡的顏色", "#00f900")
        city = c4.text_input("居住城市", "Taipei")

    # Premium 功能控制
    if st.session_state.is_premium:
        superpower = st.selectbox("⚡ 超能力", ["無", "隱形", "飛行", "噴火"])
        theme = st.selectbox("主題", ["上學焦慮", "勇氣", "分享", "專注力"])
    else:
        superpower = st.selectbox("⚡ 超能力", ["無"], disabled=True)
        theme = st.selectbox("主題", ["冒險", "日常生活", "友誼"])
    
    length_str = st.select_slider("故事長度", options=list(WORD_COUNTS.keys()))
    style = st.radio("風格", ["溫馨", "冒險", "搞笑"], horizontal=True)

    if st.button("✨ 產生故事 & 語音檔", type="primary", use_container_width=True):
        if not hero:
            st.warning("請輸入主角名字！")
        elif not API_KEY:
            # 再次檢查 API Key
            st.error("❌ 請先設定 API Key 才能生成故事！")
        else:
            with st.spinner("AI 正在編寫故事..."):
                extras = {"pet": pet, "city": city, "color": color, "superpower": superpower}
                result = generate_story_with_gemini(hero, theme, level_key, WORD_COUNTS[length_str], style, extras)
                
                if result:
                    # 確保 story 字段存在
                    story_text = result.get('story', 'Story generation failed.')
                    audio_fp = generate_audio_gtts(story_text)
                    
                    st.session_state.current_story = {
                        "title": f"{hero}'s {theme}", "text": story_text,
                        "vocab": result.get('vocab', []), "audio": audio_fp, "level": level_key
                    }
                    st.success("生成成功！")

    # 顯示當前故事
    if st.session_state.current_story:
        data = st.session_state.current_story
        st.markdown("---")
        st.markdown(f"### {data['title']}")
        
        # 顯示音頻播放器
        if data['audio']: st.audio(data['audio'], format='audio/mp3')
        
        # 顯示故事文字
        st.write(data['text'])
        
        # 顯示關鍵單字
        st.info(f"🔑 關鍵單字: {', '.join(data['vocab'])}")
        
        if st.button("💾 存入圖書館"):
            entry = f"{data['title']} ({data['level']})"
            if entry not in st.session_state.library:
                st.session_state.library.append(entry)
                st.toast("已存入圖書館！")

# --- Tab 3: Library ---
with tab3:
    st.subheader("📚 我的書櫃")
    if not st.session_state.library:
        st.write("書櫃是空的。")
    else:
        for book in st.session_state.library:
            st.info(f"📖 {book}")

# --- Tab 4: Hot ---
with tab4:
    st.subheader("🔥 熱門主題 (Premium)")
    cols = st.columns(3)
    titles = ["🧠 ADHD 專注力", "🌍 十萬個為什麼", "🏰 經典改編"]
    for i, title in enumerate(titles):
        with cols[i]:
            st.markdown(f"### {title}")
            if st.session_state.is_premium:
                st.button("閱讀", key=f"hot_{i}")
            else:
                st.button("鎖定 🔒", disabled=True, key=f"hot_lock_{i}")

# --- Tab 5: Tool ---
with tab5:
    st.subheader("⚙️ 設定")
    check_premium = st.toggle("啟用 Premium 會員 (模擬)", value=st.session_state.is_premium)
    if check_premium != st.session_state.is_premium:
        st.session_state.is_premium = check_premium
        st.rerun()

    if db:
        st.markdown("---")
        st.subheader("後台資訊 (Firebase 模擬)")
        st.info(f"App ID: {APP_ID} | User ID: {USER_ID}")
    else:
        st.warning("⚠️ Firebase 服務未啟用或初始化失敗。")

