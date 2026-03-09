# -*- coding: utf-8 -*-
"""
AI 萬用競品探測雷達 (六大維度健檢 + 競品標籤化)
- 已移除 URL 深度驗證（降低 API 消耗與錯誤）
- 競品標籤化：例如「高價專業版」「平價套路版」供後續分類
- 產出：competitors.json（供流程整合讀取）、stage1_report.md（第一階段報表）
"""

import json
import os
import re
import time
from datetime import datetime
from google import genai

try:
    from output_utils import get_report_output_dir
except ImportError:
    def get_report_output_dir(base_name="reports"):
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        folder = f"{base_name}_{ts}"
        os.makedirs(folder, exist_ok=True)
        return folder

# 先載入 config，讓 system.env 的 GEMINI_API_KEY 可被讀到
try:
    import config  # noqa: F401
except ImportError:
    pass

# --- 設定常數 ---
# 優先使用環境變數 GEMINI_API_KEY（由 system.env 載入）
import os as _os
api_key = _os.getenv("GEMINI_API_KEY", "")

# ==========================================
# 引擎一：自有品牌深度健檢 Prompt
# ==========================================
PROMPT_BRAND = """你是一位頂尖的品牌審計專家，具備即時上網搜尋的能力。
請針對以下品牌進行「深度現況調查」：
- 品牌名稱：「{brand}」
- 品牌型態：「{entity_type}」
- 產品/服務：「{service}」
- 所屬產業：「{industry}」

任務一：六大維度深度分析
請以專業行銷顧問的角度，分析該品牌並填寫以下六個維度：
1. status (狀態)：簡述目前在市場上的聲量狀態。
2. analysis (分析)：精要說明其市場定位與核心價值。
3. existing_products (現有產品)：列出目前查得到的產品或服務。
4. brand_advantages (品牌優勢)：這個品牌最大的武器是什麼？
5. fan_profile (目前的粉絲輪廓)：具體描述受眾樣貌與痛點。
6. potential (潛力)：該品牌未來可以擴展的商機。

任務二：社群媒體盤點
請搜尋其 YouTube, Instagram, Facebook, Threads, TikTok。若找不到請嘗試搜尋「{brand} Linktree」。

請以 JSON 格式回傳，格式如下：
{{
  "has_data": true 或 false,
  "status": "狀態描述...",
  "analysis": "定位分析...",
  "existing_products": "現有產品清單...",
  "brand_advantages": "優勢描述...",
  "fan_profile": "粉絲輪廓與痛點...",
  "potential": "市場潛力與建議...",
  "social_media": [
    {{"platform": "YouTube", "url": "網址或查無資料", "followers": "粉絲數或查無資料"}},
    {{"platform": "Instagram", "url": "網址或查無資料", "followers": "粉絲數或查無資料"}}
  ]
}}
"""

# ==========================================
# 引擎二：市場競品掃描 Prompt
# ==========================================
PROMPT_COMPETITORS = """你是一位市場調查專家，具備即時上網搜尋的能力。
請在「{industry}」產業中，針對「{audience}」這個受眾群體，尋找競爭對手。
（請排除品牌：「{brand}」）

【致命限制條件】對手的核心產品必須與使用者輸入的「{service}」高度相關！
例如：如果服務是大型機具、雲梯車搬運，絕對不能找一般的居家整理、清潔或純人力搬家公司。
請確保產品屬性嚴格一致！

任務：找出 10 個台灣市場「知名度最高、聲量最大」的直接競爭對手。(若不足請寧缺勿濫)
1. 受眾重合即競品：只要解決相同痛點，無論個人或企業都列入。
2. 關鍵字：主打課程、書籍或核心招牌商品。
3. 粉絲痛點：精準剖析他們解決了受眾什麼深層焦慮。

【重要】每個競品需加上「標籤」，便於後續分類：
例如：高價專業版、平價套路版、網紅IP型、企業品牌型、新創小眾型 等。

請以 JSON 格式回傳：
[
  {{
    "competitor_name": "對手真實品牌名稱",
    "label": "競品標籤（如：高價專業版、平價套路版、網紅IP型）",
    "verification_info": "官網網址或社群頻道",
    "fan_profile": "【受眾樣貌】...【深層痛點】...",
    "keywords": ["招牌商品A", "核心功能B"]
  }}
]
"""

def call_gemini(prompt_text, key, max_retries=2):
    """加上 Try-Except 與 429 重試的強壯版 API 呼叫"""
    if key and str(key).strip() and str(key).isascii():
        client = genai.Client(api_key=key)
    else:
        client = genai.Client()

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text,
                config=genai.types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            )
            if not response or not response.text:
                print("\n[警告] Gemini API 回傳成功，但內容為空 (可能觸發安全審查機制)。")
                return None
            return response.text

        except Exception as e:
            err_msg = str(e)
            if '429' in err_msg or 'RESOURCE_EXHAUSTED' in err_msg:
                if attempt < max_retries:
                    wait_sec = 60 * (attempt + 1)  # 60, 120 秒
                    print(f"\n[系統提示] API 已達限制，{wait_sec} 秒後自動重試 ({attempt + 1}/{max_retries})…")
                    time.sleep(wait_sec)
                else:
                    print("\n[系統提示] API 呼叫太頻繁已達免費限制。請稍候數分鐘後再執行。")
                    return None
            else:
                print(f"\n[API 錯誤攔截] 呼叫 Gemini 時發生問題：{e}")
                return None

    return None

def extract_json(text):
    """加上空值檢查的 JSON 解析器"""
    # 【修復 Bug 的關鍵】：如果 text 是 None，就直接提早結束，不要執行 .strip()
    if not text:
        return None
        
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("\n[除錯訊息] 無法解析 JSON，AI 回傳的內容格式有誤。")
        return None


def _fmt_products(val):
    """將 existing_products 轉成條列式字串（支援陣列或字串）"""
    if val is None:
        return "（查無資料）"
    if isinstance(val, list):
        return "\n".join(f"  - {str(item).strip()}" for item in val if item)
    return f"  {str(val).strip()}"


def _save_stage1_output(output_dir, brand, industry, brand_data, comp_data):
    """寫入 competitors.json 與 stage1_report.md"""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    # competitors.json（供 orchestrator 讀取關鍵字）
    competitors_file = os.path.join(output_dir, "competitors.json")
    payload = {
        "brand": brand,
        "industry": industry,
        "generated_at": datetime.now().isoformat(),
        "brand_health": brand_data,
        "competitors": comp_data if isinstance(comp_data, list) else [],
    }
    with open(competitors_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # 第一階段報表
    report_file = os.path.join(output_dir, f"stage1_report_{ts}.md")
    lines = [
        "# 第一階段：雷達掃描報告",
        f"品牌：{brand}｜產業：{industry}",
        f"產出時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 一、品牌六大維度健檢",
        ""
    ]
    if brand_data:
        lines.extend([
            f"- **市場狀態**：{brand_data.get('status', '（查無資料）')}",
            f"- **定位分析**：{brand_data.get('analysis', '（查無資料）')}",
            f"- **現有產品**：{_fmt_products(brand_data.get('existing_products'))}",
            f"- **品牌優勢**：{brand_data.get('brand_advantages', '（查無資料）')}",
            f"- **粉絲輪廓**：{brand_data.get('fan_profile', '（查無資料）')}",
            f"- **未來潛力**：{brand_data.get('potential', '（查無資料）')}",
            "",
        ])
    else:
        lines.append("（未取得品牌分析結果）\n")
    lines.append("## 二、競品與搜尋關鍵字\n")
    if comp_data and isinstance(comp_data, list):
        for i, c in enumerate(comp_data, 1):
            name = c.get("competitor_name") or c.get("competitor") or c.get("name") or "未知"
            label = c.get("label") or "（未標籤）"
            verification = (c.get("verification_info") or c.get("verification") or "（查無資料）").strip()
            fan_profile = c.get("fan_profile") or "（查無資料）"
            keywords = c.get("keywords") or c.get("keyword") or []
            if isinstance(keywords, str):
                keywords = [keywords]
            lines.append(f"### 競品 {i}：{name}")
            lines.append(f"- **標籤**：{label}")
            lines.append(f"- **來源**：{verification}")
            lines.append(f"- **輪廓**：{fan_profile}")
            lines.append("- **關鍵字**：" + ("、".join(keywords) if keywords else "（查無資料）"))
            lines.append("")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return competitors_file, report_file


def run_competitor_analysis(brand, entity_type, service, industry, audience, key=None, output_dir=None):
    """
    執行第一階段：品牌健檢 + 競品掃描。
    若 output_dir 為 None，則建立 competitor_reports_YYYYMMDD_HHMM。
    回傳 (brand_data, comp_data, output_dir)；並寫入 competitors.json、stage1_report_*.md。
    """
    if output_dir is None:
        output_dir = get_report_output_dir("competitor_reports")
    os.makedirs(output_dir, exist_ok=True)

    key = key or api_key
    if not key or "請在這裡填入你的API_KEY" in str(key):
        print("\n錯誤：請先填寫 API 金鑰！")
        return None, None, output_dir

    print(f"\n[引擎 1/2] 正在深度肉搜「{brand}」...")
    prompt_1 = PROMPT_BRAND.format(brand=brand, entity_type=entity_type, service=service, industry=industry)
    raw_brand = call_gemini(prompt_1, key)
    brand_data = extract_json(raw_brand)
    if brand_data:
        print("\n【品牌六大維度健檢結果】")
        print(f"► 市場狀態：{brand_data.get('status', '（查無資料）')}")
        print(f"► 定位分析：{brand_data.get('analysis', '（查無資料）')}")
        print(f"► 現有產品：{_fmt_products(brand_data.get('existing_products'))}")
        print(f"► 品牌優勢：{brand_data.get('brand_advantages', '（查無資料）')}")
        print(f"► 粉絲輪廓：{brand_data.get('fan_profile', '（查無資料）')}")
        print(f"► 未來潛力：{brand_data.get('potential', '（查無資料）')}")
    else:
        print("\n[引擎 1] 無法取得品牌分析結果。")

    time.sleep(6)
    print(f"\n[引擎 2/2] 正在掃描「{industry}」產業競品...")
    prompt_2 = PROMPT_COMPETITORS.format(brand=brand, industry=industry, audience=audience, service=service)
    raw_competitors = call_gemini(prompt_2, key)
    comp_data = extract_json(raw_competitors)
    if comp_data and isinstance(comp_data, list):
        print("\n【競品與精準搜尋關鍵字】")
        for i, c in enumerate(comp_data, 1):
            name = c.get("competitor_name") or c.get("competitor") or c.get("name") or "未知"
            label = c.get("label") or "（未標籤）"
            verification = (c.get("verification_info") or c.get("verification") or "（查無資料）").strip()
            fan_profile = c.get("fan_profile") or "（查無資料）"
            keywords = c.get("keywords") or c.get("keyword") or []
            if isinstance(keywords, str):
                keywords = [keywords]
            print(f"\n【競品 {i}】{name}｜標籤：{label}")
            print(f"├─ 來源：{verification}")
            print(f"├─ 輪廓：{fan_profile}")
            print("├─ 關鍵字：" + ("、".join(keywords) if keywords else "（查無資料）"))
    elif comp_data and not isinstance(comp_data, list):
        print("\n[引擎 2] 競品資料格式異常（預期為陣列）。")
        comp_data = []
    else:
        comp_data = []

    json_path, report_path = _save_stage1_output(output_dir, brand, industry, brand_data, comp_data)
    print(f"\n[*] 第一階段報表已儲存至：{output_dir}")
    print(f"    - competitors.json：{json_path}")
    print(f"    - 階段一報告：{report_path}")
    return brand_data, comp_data, output_dir


def main():
    print("=" * 65)
    print("AI 萬用競品探測雷達 (六大維度健檢 + 競品標籤化)")
    print("=" * 65)
    print("\n【請提供分析目標資訊】")
    brand = input("1. 品牌名稱 (例: 東區德、屋馬燒肉、Omi交友)：\n👉 ").strip()
    if not brand:
        return
    entity_type = input("2. 品牌型態 (例: 個人IP、網紅、實體企業、軟體新創)：\n👉 ").strip()
    service = input("3. 主打產品或服務 (例: 線上約會課程、單點精緻燒肉)：\n👉 ").strip()
    industry = input("4. 所屬產業或商業模式 (例: 知識付費/線上課程、餐飲業)：\n👉 ").strip()
    audience = input("5. 目標受眾與痛點 (例: 25-35歲想脫單的男性)：\n👉 ").strip()
    run_competitor_analysis(brand, entity_type, service, industry, audience, api_key, output_dir=None)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()