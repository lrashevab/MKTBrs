# -*- coding: utf-8 -*-
"""
競品輿情分析系統 - 指揮中心（main_controller.py）
第一階段：輸入與關鍵字擴充
  讓使用者輸入品牌與競品名稱，透過 Gemini 擴充出鄉民常用的別稱，
  作為後續輿情搜尋的關鍵字。
"""

# --- 引入需要的工具（套件）---
import os  # 用來讀取環境變數（例如 GEMINI_API_KEY）
from google import genai  # 官方 Gemini API 套件（需先執行：pip install google-genai）

# 先載入 config，讓 system.env 的 GEMINI_API_KEY 可被讀到
try:
    import config  # noqa: F401
except ImportError:
    pass

# --- 設定常數 ---
# API 金鑰：優先從 system.env / 環境變數 GEMINI_API_KEY 讀取
api_key = os.getenv("GEMINI_API_KEY", "")

# 送給 Gemini 的 Prompt： instruct 它扮演資深行銷，針對品牌名稱擴充出
# 「鄉民常用的別稱或關聯縮寫」（如：星巴克→星冰樂、麥當勞→麥當當）
PROMPT_TEMPLATE = """你是一位資深行銷總監，熟悉台灣網路鄉民用語與社群文化。

請針對以下兩個品牌/產品名稱，分別擴充出 3 個「鄉民常用的別稱或關聯縮寫」。
（例如：星巴克 → 可能擴充出 星冰樂、小七咖啡、統二 等；麥當勞 → 麥當當、大麥克、金拱門 等）

格式請嚴格依照以下輸出，不要多餘說明：
【我方品牌】
1. 別稱一
2. 別稱二
3. 別稱三

【競品品牌】
1. 別稱一
2. 別稱二
3. 別稱三

---
我方品牌/產品：{my_brand}
競品品牌/產品：{competitor_brand}
"""


def expand_keywords(my_brand, competitor_brand, key):
    """
    呼叫 Gemini API，將「我方品牌」與「競品品牌」分別擴充出 3 個鄉民常用別稱
    參數：
      my_brand：我方品牌/產品名稱
      competitor_brand：競品品牌/產品名稱
      key：Gemini API 金鑰
    回傳：Gemini 產生的擴充結果（字串）
    """
    # 用 format() 把品牌名稱填進 Prompt 的 {my_brand}、{competitor_brand}
    prompt = PROMPT_TEMPLATE.format(
        my_brand=my_brand.strip(),
        competitor_brand=competitor_brand.strip(),
    )

    # 若 key 為有效 ASCII，則帶入 Client；否則改用環境變數（genai.Client 會自動讀取）
    if key and key.strip() and key.isascii():
        client = genai.Client(api_key=key)
    else:
        client = genai.Client()

    # 呼叫 Gemini 2.5 Flash 模型，送出 prompt，取得文字回覆
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def main():
    """主程式：輸入品牌 → 呼叫 Gemini 擴充關鍵字 → 印出結果"""
    print("=" * 50)
    print("競品輿情分析系統 - 第一階段：關鍵字擴充")
    print("=" * 50)

    # --- 步驟一：在終端機請使用者輸入 (a) 我方品牌 (b) 競品品牌 ---
    # input() 會等待使用者輸入後按 Enter，.strip() 移除前後空白
    my_brand = input("\n請輸入「你的品牌/產品名稱」：").strip()
    if not my_brand:
        print("未輸入，程式結束。")
        return

    # (b) 競品品牌
    competitor_brand = input("請輸入「競品的品牌/產品名稱」：").strip()  # (b) 競品
    if not competitor_brand:
        print("未輸入，程式結束。")
        return

    # --- 步驟二：讀取 API 金鑰並驗證（金鑰須為 ASCII 才能通過 HTTP 編碼）---
    if not api_key or not api_key.strip():
        print("\n錯誤：未設定 API 金鑰。請在程式中設定 api_key，或設定環境變數 GEMINI_API_KEY")
        return
    if not api_key.isascii():
        print("\n錯誤：API 金鑰只能包含英文與數字，不可含中文。")
        return

    # --- 步驟三：將兩個品牌名稱傳給 Gemini，請它擴充出鄉民常用別稱 ---
    print("\n正在呼叫 Gemini 擴充關鍵字...")
    result = expand_keywords(my_brand, competitor_brand, api_key)

    # --- 步驟四：將 Gemini 回傳的擴充結果印在終端機上 ---
    print("\n" + "=" * 50)
    print("【擴充後的關鍵字清單】")
    print("=" * 50)
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    main()
