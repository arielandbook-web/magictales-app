import requests
import json

# ==========================================================
# 🚨 貼上您實際的金鑰到這裡，然後執行
# ==========================================================
API_KEY_TO_TEST = "AIzaSyA-HXh3jtRevDRwZ5P1MWGMdUKllxQpnYo" # 範例: AIzaSyC...
# ==========================================================

MODEL = "gemini-2.5-flash"
BASE_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY_TO_TEST}"

# 測試用的簡單請求
PROMPT = "Say hello to the world in a brief sentence."

headers = {'Content-Type': 'application/json'}
payload = {
    "contents": [{"parts": [{"text": PROMPT}]}],
}

print(f"--- 開始測試 Gemini 模型連線 ({MODEL}) ---")

try:
    response = requests.post(BASE_URL, headers=headers, json=payload, timeout=20)
    
    # 檢查 HTTP 狀態碼
    if response.status_code == 200:
        # 如果狀態碼是 200，嘗試解析 JSON
        result = response.json()
        
        # 檢查模型是否有返回內容
        if 'candidates' in result and result['candidates'][0]['content']['parts'][0]['text']:
            print("✅ 測試成功！金鑰有效且可以連線到模型。")
            print(f"🤖 模型回應: {result['candidates'][0]['content']['parts'][0]['text'].strip()}")
            print("→ 請確認此金鑰已正確貼到 Streamlit Secrets 中。")
        else:
            print("⚠️ 測試成功，但模型回應異常。可能是請求或金鑰權限問題。")

    else:
        # 狀態碼不是 200，表示金鑰或服務有問題
        print(f"❌ 測試失敗！HTTP 狀態碼: {response.status_code}")
        
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', '無具體錯誤訊息')
            print(f"🚨 Google 錯誤訊息: {error_message}")
            
            if "API key not valid" in error_message or "API key is not valid" in error_message:
                print("🚨 結論：**金鑰格式或本身錯誤**，請在 Google AI Studio 重新生成一個。")
            elif "NOT_FOUND" in error_message:
                print("🚨 結論：**模型找不到**，請檢查金鑰的權限是否支援 gemini-2.5-flash。")
            elif "Billing" in error_message:
                print("🚨 結論：**計費功能未開啟**，請到 Google Cloud Console 啟用計費。")

        except json.JSONDecodeError:
            print("🚨 結論：伺服器回應格式異常，金鑰可能無效。")

except requests.exceptions.RequestException as e:
    print(f"❌ 網路連線錯誤或超時: {e}")
    print("🚨 結論：請檢查網路連線。")

print("------------------------------------------")

