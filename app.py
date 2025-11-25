import streamlit as st
import time
import json
import requests
import random
from datetime import datetime
import io

# 引入 gTTS 用於穩定的語音合成
from gtts import gTTS

# --- 1. App 基礎設定 ---
st.set_page_config(
    page_title="MagicTales",
    page_icon="🦄",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. 載入 Secrets (API Key & Firebase) ---
try:
    API_KEY = st.secrets["gemini_api_key"]
except:
    API_KEY = ""
    # 在側邊欄顯示警告，但不影響主畫面
    # st.sidebar.error("⚠️ 未設定 Gemini API Key")

# 定義最穩定的模型名稱
BASE_API_URL = "https://generativelanguage.googleapis.com/v1/models/"
MODEL_TEXT = "gemini-2.5-flash"

# --- 3. Firebase 初始化 (靜默模式) ---
# 我們使用廣泛的 try-except 確保 Firebase 錯誤不會讓 App 崩潰或顯示紅色警告
db = None
USER_ID = "guest_user"

try:
    from firebase_admin import initialize_app, credentials, firestore
    from google.cloud import firestore as gcf
    
    if not gcf.Client()._app:
        # 嘗試讀取 Firebase 設定
        if "__firebase_config" in st.secrets:
            firebase_config = json.loads(st.secrets["__firebase_config"])
            cred = credentials.Certificate(firebase_config)
            initialize_app(cred)
            db = firestore.client()
            USER_ID = "stream_user_123"
except Exception:
    # 如果失敗，靜默切換到模擬模式，不顯示錯誤
    db = None

APP_ID = st.secrets.get("__app_id", "default-app-id")

# --- 4. 載入 CSS (樣式優化) ---
# 為了避免找不到檔案報錯，我們直接把 CSS 寫在程式碼裡
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


# --- 5. 初始化 Session State ---
if 'library' not in st.session_state: st.session_state.library = []
if 'is_premium' not in st.session_state: st.session_state.is_premium = False
if 'current_story' not in st.session_state: st.session_state.current_story = None

# 定義常數
CEFR_HINTS = {
    "A0": "入門：150字內。極簡短句，適合剛接觸英文的幼兒。",
    "A1": "初級：250字內。簡單日常用語，適合小學低年級。",
    "A1+": "初級進階：350字內。能理解常見句子，適合小學中年級。",
    "A2": "基礎：500字內。能描述簡單背景，適合小學高年級。",
    "A2+": "基礎進階：700字內。能處理簡單交流，國中預備。",
    "B1": "中級：1000字內。能應對旅行、生活主題。",
    "B2": "中高級：1500字內。複雜抽象概念。"
}

WORD_COUNTS = {
    "3 分鐘": 300, "5 分鐘": 500, "8 分鐘": 800, "12 分鐘": 1200
}

# --- 6. 核心功能函數 ---

def generate_story_with_gemini(hero, theme, level, word_count, style, extras):
    """呼叫 Gemini 1.5 Flash 生成故事"""
    if not API_KEY:
        st.error("❌ 請先設定 API Key 才能生成故事！")
        return None

    # 構建 Prompt
    prompt = (
        f"You are a children's English storyteller. Write a story strictly following these rules:\n"
        f"1. Hero: {hero} (Pet: {extras['pet']}).\n"
        f"2. Setting: {extras['city']}. Favorite Color: {extras['color']}.\n"
        f"3. Theme: {theme}. Style: {style}.\n"
        f"4. Level: {level}. Length: approx {word_count} words.\n"
        f"5. Superpower: {extras['superpower']}.\n"
        f"6. Output Format: Return a raw JSON object with exactly two keys: 'story' (string) and 'vocab' (list of 5 strings).\n"
        f"Do not include markdown formatting like ```json."
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
        
        # 解析 JSON
        return json.loads(text_content)
        
    except Exception as e:
        st.error(f"生成失敗，請重試。錯誤原因: {e}")
        return None

def generate_audio_gtts(text):
    """使用 gTTS 生成 MP3 (穩定版)"""
    try:
        # 使用 Google Translate TTS 引擎
        tts = gTTS(text=text, lang='en', slow=False)
        
        # 寫入記憶體 (BytesIO)，不需要存成檔案
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except Exception as e:
        st.warning(f"語音生成暫時無法使用: {e}")
        return None

# --- 7. UI 介面 ---

st.title("MagicTales 兒童英語故事屋 📖")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "✨ Story Request", "📚 Library", "🔥 Hot", "🛠️ Tool"])

# --- Tab 1: Home ---
with tab1:
    st.subheader("歡迎回來！")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("本週閱讀", "3 篇")
    with col2:
        st.metric("閱讀進度", "Level A1")
    
    st.progress(0.4, text="距離升級還差 60%")
    
    st.markdown("### 🏆 經典故事")
    c1, c2 = st.columns(2)
    c1.button("Three Little Pigs", use_container_width=True)
    c2.button("Little Red Riding Hood", use_container_width=True)

    if st.session_state.is_premium:
        st.success("👑 Premium 會員已啟用：您可以閱讀熱門故事！")
    else:
        st.info("💡 升級 Premium 解鎖更多功能！")

# --- Tab 2: Story Request (核心) ---
with tab2:
    st.subheader("✨ 創建專屬故事")
    
    # 分級選擇
    level_key = st.selectbox("選擇 CEFR 等級", list(CEFR_HINTS.keys()))
    st.markdown(f'<div class="cefr-hint">{CEFR_HINTS[level_key]}</div>', unsafe_allow_html=True)
    
    # 客製化選項
    with st.container(border=True):
        st.caption("主角設定")
        c1, c2 = st.columns(2)
        hero = c1.text_input("主角名字 (英文)", "Leo")
        pet = c2.text_input("寵物名字", "Rex")
        
        c3, c4 = st.columns(2)
        color = c3.color_picker("喜歡的顏色", "#00f900")
        city = c4.text_input("居住城市", "Taipei")

    # Premium 選項
    st.markdown("---")
    if st.session_state.is_premium:
        superpower = st.selectbox("⚡ 超能力 (VIP)", ["無", "隱形", "飛行", "噴火"])
        theme = st.selectbox("主題 (VIP)", ["上學焦慮", "勇氣", "分享", "專注力"])
    else:
        superpower = st.selectbox("⚡ 超能力 (VIP)", ["無"], disabled=True)
        theme = st.selectbox("主題", ["冒險", "日常生活", "友誼"])
        st.caption("🔒 升級 Premium 解鎖超能力與特殊主題！")

    # 長度與風格
    length_str = st.select_slider("故事長度", options=list(WORD_COUNTS.keys()))
    style = st.radio("風格", ["溫馨", "冒險", "搞笑"], horizontal=True)

    # 生成按鈕
    if st.button("✨ 產生故事 & 語音檔", type="primary", use_container_width=True):
        if not hero:
            st.warning("請輸入主角名字！")
        else:
            with st.spinner("AI 正在編寫故事並錄製語音..."):
                # 1. 生成文字
                extras = {"pet": pet, "city": city, "color": color, "superpower": superpower}
                result = generate_story_with_gemini(hero, theme, level_key, WORD_COUNTS[length_str], style, extras)
                
                if result:
                    # 2. 生成語音
                    audio_fp = generate_audio_gtts(result['story'])
                    
                    # 3. 存入暫存
                    st.session_state.current_story = {
                        "title": f"{hero}'s {theme} Adventure",
                        "text": result['story'],
                        "vocab": result['vocab'],
                        "audio": audio_fp,
                        "level": level_key
                    }
                    st.success("生成成功！")

    # 顯示生成結果
    if st.session_state.current_story:
        data = st.session_state.current_story
        
        st.markdown("---")
        st.markdown(f"### {data['title']}")
        
        # 播放器
        if data['audio']:
            st.audio(data['audio'], format='audio/mp3')
        
        st.write(data['text'])
        
        st.info(f"🔑 關鍵單字: {', '.join(data['vocab'])}")
        
        # 自動存入圖書館按鈕
        if st.button("💾 存入圖書館", key="save_btn"):
            entry = f"{data['title']} ({data['level']})"
            if entry not in st.session_state.library:
                st.session_state.library.append(entry)
                st.toast("已存入圖書館！")

# --- Tab 3: Library ---
with tab3:
    st.subheader("📚 我的書櫃")
    search = st.text_input("搜尋故事...", "")
    
    if not st.session_state.library:
        st.write("書櫃是空的。")
    else:
        for book in st.session_state.library:
            if search.lower() in book.lower():
                st.info(f"📖 {book}")

# --- Tab 4: Hot Stories ---
with tab4:
    st.subheader("🔥 熱門主題 (Premium)")
    cols = st.columns(3)
    titles = ["ADHD 專注力", "十萬個為什麼", "經典改編"]
    
    for i, title in enumerate(titles):
        with cols[i]:
            st.image(f"[https://placehold.co/150x100?text=](https://placehold.co/150x100?text=){i+1}", use_container_width=True)
            if st.session_state.is_premium:
                st.button(title, key=f"hot_{i}")
            else:
                st.button("鎖定 🔒", disabled=True, key=f"hot_lock_{i}")

# --- Tab 5: Tool ---
with tab5:
    st.subheader("⚙️ 設定與數據")
    
    # Premium 開關
    check_premium = st.toggle("啟用 Premium 會員 (模擬)", value=st.session_state.is_premium)
    if check_premium != st.session_state.is_premium:
        st.session_state.is_premium = check_premium
        st.rerun()

    st.write("---")
    st.write("📊 **聽音頻時間記錄**")
    if db:
        st.success("雲端資料庫連線中...")
    else:
        st.warning("目前使用本地模擬模式 (資料不會上傳雲端)")

    st.slider("今日聽力目標 (分鐘)", 0, 60, 30)


