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
# 引擎一：自有品牌深度健檢 Prompt（行銷專家版）
# ==========================================
PROMPT_BRAND = """你是一位頂尖的品牌審計專家，具備即時上網搜尋的能力。
請針對以下品牌進行「深度現況調查」：
- 品牌名稱：「{brand}」
- 品牌型態：「{entity_type}」
- 產品/服務：「{service}」
- 所屬產業：「{industry}」

任務一：八大維度深度分析（行銷專家版）
請以專業行銷顧問的角度，分析該品牌並填寫以下八個維度：
1. status (市場狀態)：簡述目前在市場上的聲量狀態與市場地位。
2. analysis (定位分析)：精要說明其市場定位、核心價值與差異化。
3. existing_products (現有產品)：列出目前查得到的產品或服務，包含價格區間。
4. brand_advantages (品牌優勢)：這個品牌最大的武器是什麼？（技術/價格/品牌/通路）
5. fan_profile (受眾輪廓)：具體描述受眾樣貌、痛點、消費行為與價值觀。
6. potential (市場潛力)：該品牌未來可以擴展的商機與成長空間。
7. swot_analysis (SWOT分析)：簡要的SWOT分析（優勢/劣勢/機會/威脅）。
8. marketing_channels (行銷通路)：目前使用的行銷通路與成效評估。

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
  "swot_analysis": "優勢:..., 劣勢:..., 機會:..., 威脅:...",
  "marketing_channels": "目前使用的行銷通路...",
  "social_media": [
    {{"platform": "YouTube", "url": "網址或查無資料", "followers": "粉絲數或查無資料", "engagement_rate": "互動率或查無資料"}},
    {{"platform": "Instagram", "url": "網址或查無資料", "followers": "粉絲數或查無資料", "engagement_rate": "互動率或查無資料"}}
  ]
}}
"""

# ==========================================
# 引擎二：市場競品掃描 Prompt（行銷專家版）
# ==========================================
PROMPT_COMPETITORS = """你是一位市場調查專家，具備即時上網搜尋的能力。
請在「{industry}」產業中，針對「{audience}」這個受眾群體，尋找競爭對手。
（請排除品牌：「{brand}」）

【致命限制條件】對手的核心產品必須與使用者輸入的「{service}」高度相關！
例如：如果服務是大型機具、雲梯車搬運，絕對不能找一般的居家整理、清潔或純人力搬家公司。
請確保產品屬性嚴格一致！

任務：找出 10 個台灣市場「知名度最高、聲量最大」的直接競爭對手。(若不足請寧缺勿濫)

【行銷專家分析維度】
1. 市場定位：價格帶、目標客群、價值主張
2. 產品矩陣：核心產品、價格區間、特色功能
3. 行銷策略：主要行銷通路、內容策略、轉換漏斗
4. 品牌聲量：社群影響力、媒體曝光、口碑評價
5. 競爭優勢：技術/價格/品牌/通路/服務優勢
6. 威脅分析：市場威脅、潛在替代品

【重要】每個競品需加上「標籤」，便於後續分類：
例如：高價專業版、平價套路版、網紅IP型、企業品牌型、新創小眾型、技術領先型、通路優勢型。

請以 JSON 格式回傳：
[
  {{
    "competitor_name": "對手真實品牌名稱",
    "label": "競品標籤（如：高價專業版、平價套路版、網紅IP型）",
    "verification_info": "官網網址或社群頻道",
    "fan_profile": "【受眾樣貌】...【深層痛點】...",
    "keywords": ["招牌商品A", "核心功能B"],
    "price_range": "價格區間（如：NT$1,000-3,000）",
    "market_position": "市場定位描述",
    "strengths": "主要優勢（技術/價格/品牌/通路）",
    "weaknesses": "潛在弱點",
    "social_presence": "社群影響力評估（高/中/低）",
    "recommended_strategy": "建議應對策略"
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
    """寫入 competitors.json 與 stage1_report.md（行銷專家版）"""
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
    # 第一階段報表（行銷專家版）
    report_file = os.path.join(output_dir, f"stage1_report_{ts}.md")
    lines = [
        "# 第一階段：競品雷達掃描報告（行銷專家版）",
        f"品牌：{brand}｜產業：{industry}",
        f"產出時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 📊 執行摘要（Executive Summary）",
        "",
        f"### 市場概況",
        f"- **分析品牌**：{brand}",
        f"- **產業類別**：{industry}",
        f"- **競品數量**：{len(comp_data) if isinstance(comp_data, list) else 0} 個",
        f"- **主要發現**：市場競爭激烈，建議採取差異化定位策略",
        "",
        "## 🎯 品牌八大維度深度分析",
        ""
    ]
    if brand_data:
        lines.extend([
            f"### 1. 市場狀態",
            f"{brand_data.get('status', '（查無資料）')}",
            "",
            f"### 2. 定位分析",
            f"{brand_data.get('analysis', '（查無資料）')}",
            "",
            f"### 3. 現有產品矩陣",
            f"{_fmt_products(brand_data.get('existing_products'))}",
            "",
            f"### 4. 品牌核心優勢",
            f"{brand_data.get('brand_advantages', '（查無資料）')}",
            "",
            f"### 5. 目標受眾輪廓",
            f"{brand_data.get('fan_profile', '（查無資料）')}",
            "",
            f"### 6. 市場潛力評估",
            f"{brand_data.get('potential', '（查無資料）')}",
            "",
            f"### 7. SWOT 分析",
            f"{brand_data.get('swot_analysis', '（查無資料）')}",
            "",
            f"### 8. 行銷通路現況",
            f"{brand_data.get('marketing_channels', '（查無資料）')}",
            "",
        ])
    else:
        lines.append("（未取得品牌分析結果）\n")
    lines.append("## ⚔️ 競品深度分析")
    lines.append("")
    if comp_data and isinstance(comp_data, list):
        # 競品分類統計
        labels = [c.get("label", "未分類") for c in comp_data]
        label_counts = {}
        for label in labels:
            label_counts[label] = label_counts.get(label, 0) + 1
        
        lines.append("### 競品分類統計")
        for label, count in label_counts.items():
            lines.append(f"- **{label}**：{count} 個")
        lines.append("")
        
        for i, c in enumerate(comp_data, 1):
            name = c.get("competitor_name") or c.get("competitor") or c.get("name") or "未知"
            label = c.get("label") or "（未標籤）"
            verification = (c.get("verification_info") or c.get("verification") or "（查無資料）").strip()
            fan_profile = c.get("fan_profile") or "（查無資料）"
            keywords = c.get("keywords") or c.get("keyword") or []
            price_range = c.get("price_range", "未標示")
            market_position = c.get("market_position", "未分析")
            strengths = c.get("strengths", "未分析")
            weaknesses = c.get("weaknesses", "未分析")
            social_presence = c.get("social_presence", "未評估")
            recommended_strategy = c.get("recommended_strategy", "未提供")
            
            if isinstance(keywords, str):
                keywords = [keywords]
            
            lines.append(f"### 競品 {i}：{name}")
            lines.append(f"- **標籤分類**：{label}")
            lines.append(f"- **價格區間**：{price_range}")
            lines.append(f"- **市場定位**：{market_position}")
            lines.append(f"- **來源驗證**：{verification}")
            lines.append(f"- **受眾輪廓**：{fan_profile}")
            lines.append(f"- **核心關鍵字**：" + ("、".join(keywords) if keywords else "（查無資料）"))
            lines.append(f"- **主要優勢**：{strengths}")
            lines.append(f"- **潛在弱點**：{weaknesses}")
            lines.append(f"- **社群影響力**：{social_presence}")
            lines.append(f"- **建議策略**：{recommended_strategy}")
            lines.append("")
    lines.append("## 🎯 行動建議（Actionable Insights）")
    lines.append("")
    lines.append("### 短期策略（1-3個月）")
    lines.append("1. **市場定位優化**：根據競品分析調整自身定位")
    lines.append("2. **價格策略調整**：參考競品價格區間制定競爭策略")
    lines.append("3. **關鍵字優化**：針對高搜尋量關鍵字進行內容佈局")
    lines.append("")
    lines.append("### 中期策略（3-6個月）")
    lines.append("1. **產品差異化**：開發競品未滿足的市場需求")
    lines.append("2. **通路拓展**：評估競品未覆蓋的行銷通路")
    lines.append("3. **品牌建設**：強化品牌故事與價值主張")
    lines.append("")
    lines.append("### 長期策略（6-12個月）")
    lines.append("1. **市場擴張**：考慮進入競品未觸及的細分市場")
    lines.append("2. **技術創新**：投資研發建立技術壁壘")
    lines.append("3. **生態系建設**：建立品牌生態系提高用戶黏著度")
    lines.append("")
    lines.append("## 📈 數據視覺化建議")
    lines.append("")
    lines.append("### 建議圖表類型")
    lines.append("1. **競品雷達圖**：價格、聲量、口碑、技術、通路五維度對比")
    lines.append("2. **價格帶分布圖**：競品價格區間視覺化")
    lines.append("3. **市場定位矩陣**：價格 vs. 品質二維定位圖")
    lines.append("4. **社群影響力圖**：各競品社群平台粉絲數對比")
    lines.append("5. **關鍵字熱力圖**：高搜尋量關鍵字視覺化")
    
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
        print("\n" + "=" * 65)
        print("【品牌八大維度深度分析結果】")
        print("=" * 65)
        print(f"► 市場狀態：{brand_data.get('status', '（查無資料）')}")
        print(f"► 定位分析：{brand_data.get('analysis', '（查無資料）')}")
        print(f"► 現有產品：{_fmt_products(brand_data.get('existing_products'))}")
        print(f"► 品牌優勢：{brand_data.get('brand_advantages', '（查無資料）')}")
        print(f"► 粉絲輪廓：{brand_data.get('fan_profile', '（查無資料）')}")
        print(f"► 未來潛力：{brand_data.get('potential', '（查無資料）')}")
        print(f"► SWOT分析：{brand_data.get('swot_analysis', '（查無資料）')}")
        print(f"► 行銷通路：{brand_data.get('marketing_channels', '（查無資料）')}")
        print("=" * 65)
    else:
        print("\n[引擎 1] 無法取得品牌分析結果。")

    time.sleep(6)
    print(f"\n[引擎 2/2] 正在掃描「{industry}」產業競品...")
    prompt_2 = PROMPT_COMPETITORS.format(brand=brand, industry=industry, audience=audience, service=service)
    raw_competitors = call_gemini(prompt_2, key)
    comp_data = extract_json(raw_competitors)
    if comp_data and isinstance(comp_data, list):
        print("\n" + "=" * 65)
        print("【競品深度分析結果】")
        print("=" * 65)
        for i, c in enumerate(comp_data, 1):
            name = c.get("competitor_name") or c.get("competitor") or c.get("name") or "未知"
            label = c.get("label") or "（未標籤）"
            verification = (c.get("verification_info") or c.get("verification") or "（查無資料）").strip()
            fan_profile = c.get("fan_profile") or "（查無資料）"
            keywords = c.get("keywords") or c.get("keyword") or []
            price_range = c.get("price_range", "未標示")
            market_position = c.get("market_position", "未分析")
            strengths = c.get("strengths", "未分析")
            weaknesses = c.get("weaknesses", "未分析")
            social_presence = c.get("social_presence", "未評估")
            
            if isinstance(keywords, str):
                keywords = [keywords]
            
            print(f"\n【競品 {i}】{name}")
            print(f"├─ 標籤：{label}")
            print(f"├─ 價格：{price_range}")
            print(f"├─ 定位：{market_position}")
            print(f"├─ 來源：{verification}")
            print(f"├─ 輪廓：{fan_profile}")
            print(f"├─ 關鍵字：" + ("、".join(keywords) if keywords else "（查無資料）"))
            print(f"├─ 優勢：{strengths}")
            print(f"├─ 弱點：{weaknesses}")
            print(f"└─ 影響力：{social_presence}")
        print("=" * 65)
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
    print("\n" + "═" * 65)
    print("║" + " " * 27 + "⚡ MKTBrs 競品雷達系統 ⚡" + " " * 27 + "║")
    print("║" + " " * 18 + "AI-Powered Competitive Intelligence Platform" + " " * 18 + "║")
    print("═" * 65)
    print("\n📡 系統初始化中...")
    time.sleep(1)
    print("✅ 連線至 Gemini AI 引擎...")
    time.sleep(0.5)
    print("🎯 載入行銷分析框架...")
    time.sleep(0.5)
    print("\n" + "─" * 65)
    print("【請輸入分析目標資訊】")
    print("─" * 65)
    
    print("\n🔍 步驟 1/5：品牌基本資訊")
    brand = input("   品牌名稱 (例: 東區德、屋馬燒肉、Omi交友)：\n   👉 ").strip()
    if not brand:
        return
    
    print("\n🏢 步驟 2/5：品牌型態")
    entity_type = input("   品牌型態 (例: 個人IP、網紅、實體企業、軟體新創)：\n   👉 ").strip()
    
    print("\n📦 步驟 3/5：核心產品/服務")
    service = input("   主打產品或服務 (例: 線上約會課程、單點精緻燒肉)：\n   👉 ").strip()
    
    print("\n🏭 步驟 4/5：產業類別")
    industry = input("   所屬產業或商業模式 (例: 知識付費/線上課程、餐飲業)：\n   👉 ").strip()
    
    print("\n👥 步驟 5/5：目標受眾")
    audience = input("   目標受眾與痛點 (例: 25-35歲想脫單的男性)：\n   👉 ").strip()
    
    print("\n" + "─" * 65)
    print("🚀 開始深度市場分析...")
    print("─" * 65)
    
    run_competitor_analysis(brand, entity_type, service, industry, audience, api_key, output_dir=None)
    
    print("\n" + "═" * 65)
    print("║" + " " * 20 + "✅ 分析完成！報告已儲存至輸出資料夾" + " " * 20 + "║")
    print("═" * 65)
    print("\n📊 產出內容：")
    print("   • competitors.json - 競品結構化數據")
    print("   • stage1_report_*.md - 完整行銷分析報告")
    print("   • 包含：執行摘要、SWOT分析、行動建議、視覺化建議")
    print("\n🎯 下一步建議：")
    print("   1. 檢視報告中的行動建議")
    print("   2. 執行輿情分析了解市場聲量")
    print("   3. 制定差異化市場策略")
    print("\n" + "─" * 65)


if __name__ == "__main__":
    main()