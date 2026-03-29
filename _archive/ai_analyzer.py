# -*- coding: utf-8 -*-
"""
AI 輿情分析師：讀取 Dcard 文章標題，請 Gemini 分析年輕人社群話題與行銷切入點
（需先安裝：pip install pandas google-genai）
"""

# --- 引入需要的工具（套件）---
import os  # 用來讀取環境變數
import pandas as pd  # 用來讀取 CSV 並處理表格資料
from google import genai  # 官方 Gemini API 套件（google-genai）

# 先載入 config，讓 system.env 的 GEMINI_API_KEY 可被讀到
try:
    import config  # noqa: F401
except ImportError:
    pass

# --- 設定常數 ---
# API 金鑰：優先從 system.env / 環境變數 GEMINI_API_KEY 讀取
api_key = os.getenv("GEMINI_API_KEY", "")

# 輸入與輸出檔案
INPUT_CSV = "dcard_all_forums.csv"
OUTPUT_REPORT = "marketing_report.md"

# 只取前 100 篇標題，節省 API 額度與處理時間
MAX_TITLES = 100

# 要送給 Gemini 的行銷分析指令（Prompt）
PROMPT_TEMPLATE = """你現在是一位年薪三百萬的資深行銷總監。以下是最近在 Dcard 上的 100 篇熱門文章標題。請幫我分析：
(1) 目前年輕人最關注的三大話題是什麼？
(2) 如果我要推廣一款「交友約會線上課程」，這些標題中有哪些痛點或需求可以作為我的廣告切入點？
請用繁體中文，以 Markdown 格式輸出專業的分析報告。

---
以下是 100 篇標題（每行一則）：
{titles}
"""


def load_titles(csv_path, n=MAX_TITLES):
    """
    用 pandas 讀取 CSV，取出前 n 篇的「標題」欄位，組成清單
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # 取前 n 筆的「標題」欄位，轉成 Python 列表
    titles = df["標題"].head(n).tolist()
    return titles


def call_gemini(titles, key, model="gemini-2.5-flash"):
    """
    呼叫 Gemini API，把標題清單與行銷指令一併送出
    使用環境變數時可不傳 key，直接 genai.Client() 會自動讀取 GEMINI_API_KEY
    """
    # 把標題列表轉成字串（每行一則，方便 Gemini 閱讀）
    titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

    # 組合完整的 Prompt（指令 + 資料）
    prompt = PROMPT_TEMPLATE.format(titles=titles_text)

    # 建立 Gemini 客戶端：有傳 key 且為 ASCII 時才用，否則用環境變數
    if key and key.isascii():
        client = genai.Client(api_key=key)
    else:
        client = genai.Client()  # 自動讀取 GEMINI_API_KEY

    # 呼叫 generate_content：指定模型、送進 prompt，取得回覆
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    # response.text 是模型回傳的純文字內容
    return response.text


def main():
    """主程式：讀取標題 → 呼叫 Gemini → 印出並存檔"""
    # 檢查 API 金鑰：必須是純 ASCII，否則 httpx 在編碼 HTTP header 時會出錯
    if not api_key or not api_key.strip():
        print("錯誤：未設定 API 金鑰。請在程式中設定 api_key，或設定環境變數 GEMINI_API_KEY")
        return
    if not api_key.isascii():
        print("錯誤：API 金鑰只能包含英文與數字，不可含中文。")
        print("請在程式中貼上你的金鑰，或執行：set GEMINI_API_KEY=你的金鑰")
        return

    print("正在讀取 Dcard 文章標題...")

    # --- 步驟一：讀取 CSV，取前 100 篇標題 ---
    titles = load_titles(INPUT_CSV, MAX_TITLES)
    print(f"已讀取 {len(titles)} 篇標題\n")

    if not titles:
        print("錯誤：沒有讀到任何標題，請確認 dcard_all_forums.csv 存在且有資料。")
        return

    # --- 步驟二：呼叫 Gemini API 進行分析 ---
    print("正在呼叫 Gemini API（模型：gemini-2.5-flash）...\n")
    report = call_gemini(titles, api_key)

    # --- 步驟三：印在終端機上 ---
    print("=" * 60)
    print("【AI 輿情分析報告】")
    print("=" * 60)
    print(report)
    print("=" * 60)

    # --- 步驟四：存成 marketing_report.md ---
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n報告已儲存至 {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
