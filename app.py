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

# --- 2. 載入 API Key ---
try:
    API_KEY = st.secrets["gemini_api_key"]
except:
    API_KEY = ""

# API 設定
BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
MODEL_TEXT = "gemini-1.5-flash"

# --- 3. Firebase 初始化 (靜默模式) ---
db = None
USER_ID = "guest_user"
try:
    from firebase_admin import initialize_app, credentials, firestore
    from google.cloud import firestore as gcf
    if not gcf.Client()._app:
        if "__firebase_config" in st.secrets:
            firebase_config = json.loads(st.secrets["__firebase_config"])
            cred = credentials.Certificate(firebase_config)
            initialize_app(cred)
            db = firestore.client()
            USER_ID = "stream_user_123"
except Exception:
    db = None

APP_ID = st.secrets.get("__app_id", "default-app-id")

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
    if not API_KEY:
        st.error("❌ 請先設定 API Key 才能生成故事！")
        return None

    prompt = (
        f"Write a children's story (English).\n"
        f"Hero: {hero}, Pet: {extras['pet']}, City: {extras['city']}\n"
        f"Theme: {theme}, Style: {style}, Color: {extras['color']}\n"
        f"Level: {level}, Length: {word_count} words.\n"
        f"Superpower: {extras['superpower']}\n"
        f"Output JSON format strictly: {{'story': '...', 'vocab': ['w1', 'w2', 'w3', 'w4', 'w5']}}"
    )

    url = f"{BASE_API_URL}{MODEL_TEXT}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            st.error(f"API Error: {response.text}")
            return None
        result = response.json()
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(text_content)
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def generate_audio_gtts(text):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except Exception as e:
        st.warning(f"Audio Error: {e}")
        return None

# --- 7. UI 介面 ---
st.title("MagicTales 兒童英語故事屋 📖")

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
    # 這裡移除了容易出錯的圖片網址，改用簡單的 Emoji 按鈕
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
        else:
            with st.spinner("AI 正在編寫故事..."):
                extras = {"pet": pet, "city": city, "color": color, "superpower": superpower}
                result = generate_story_with_gemini(hero, theme, level_key, WORD_COUNTS[length_str], style, extras)
                if result:
                    audio_fp = generate_audio_gtts(result['story'])
                    st.session_state.current_story = {
                        "title": f"{hero}'s {theme}", "text": result['story'],
                        "vocab": result['vocab'], "audio": audio_fp, "level": level_key
                    }
                    st.success("生成成功！")

    if st.session_state.current_story:
        data = st.session_state.current_story
        st.markdown("---")
        st.markdown(f"### {data['title']}")
        if data['audio']: st.audio(data['audio'], format='audio/mp3')
        st.write(data['text'])
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
            # 這裡移除了可能崩潰的 st.image 網址
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


