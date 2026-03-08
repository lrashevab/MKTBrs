# -*- coding: utf-8 -*-
"""
市調流程整合：一次執行第一階段（競品雷達）＋第二階段（Dcard / PTT 輿情）
所有產出寫入同一個 campaign_YYYYMMDD_HHMM 資料夾。
"""

import json
import os
import sys

# 先載入 config，讓 system.env 的 GEMINI_API_KEY 可被讀到
try:
    import config  # noqa: F401
except ImportError:
    pass

try:
    from output_utils import get_campaign_output_dir
except ImportError:
    def get_campaign_output_dir():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        folder = f"campaign_{ts}"
        os.makedirs(folder, exist_ok=True)
        return folder


def _collect_keywords_from_competitors(comp_data, max_keywords=3):
    """從競品列表抽出關鍵字（優先取品牌名，並嚴格限制數量避免被 Dcard 封鎖 IP）"""
    seen = set()
    keywords_list = []
    
    # 優先把「競品品牌名稱」當作關鍵字
    for c in (comp_data or []):
        name = c.get("competitor_name") or c.get("competitor") or c.get("name")
        if name and isinstance(name, str) and name.strip() and name.strip() not in seen:
            seen.add(name.strip())
            keywords_list.append(name.strip())
            
    # 如果品牌名不夠，再拿他們的核心產品詞來湊
    for c in (comp_data or []):
        kws = c.get("keywords") or c.get("keyword") or []
        if isinstance(kws, str): kws = [kws]
        for kw in kws:
            if kw and isinstance(kw, str) and kw.strip() and kw.strip() not in seen:
                seen.add(kw.strip())
                keywords_list.append(kw.strip())

    # 絕對不能超過 max_keywords (預設 3 個)，否則會被 Dcard 視為 DDoS 攻擊
    return keywords_list[:max_keywords]


def run():
    print("=" * 60)
    print("  市調流程整合（第一階段 + 第二階段）")
    print("  所有產出將寫入同一個 campaign 資料夾")
    print("=" * 60)

    campaign_dir = get_campaign_output_dir()
    print(f"\n[*] 本次專案資料夾：{campaign_dir}\n")

    # --- 第一階段：競品雷達 ---
    print("【第一階段】競品雷達掃描")
    brand = input("  品牌名稱：").strip()
    if not brand:
        print("未輸入品牌，結束。")
        return
    entity_type = input("  品牌型態（例：個人IP、實體企業）：").strip()
    service = input("  主打產品或服務：").strip()
    industry = input("  所屬產業（例：餐飲業、知識付費）：").strip()
    audience = input("  目標受眾與痛點：").strip()

    from auto_competitor_finder import run_competitor_analysis, api_key
    brand_data, comp_data, _ = run_competitor_analysis(
        brand, entity_type, service, industry, audience,
        key=api_key,
        output_dir=campaign_dir,
    )

    keywords = _collect_keywords_from_competitors(comp_data)
    if not keywords:
        keywords = [service or brand]
    print(f"\n[*] 將使用以下關鍵字進行第二階段：{keywords[:15]}{'...' if len(keywords) > 15 else ''}")

    # --- 第二階段：Dcard ---
    print("\n【第二階段】Dcard 輿情搜尋")
    run_dcard = input("  是否執行 Dcard？(y/n，預設 y)：").strip().lower() != "n"
    time_range_days = 180
    choice = input("  時間範圍 1=1月 2=半年 3=1年 (預設 2)：").strip() or "2"
    time_range_days = {"1": 30, "2": 180, "3": 365}.get(choice, 180)

    if run_dcard:
        from dcard_scraper import run_dcard_scrape
        run_dcard_scrape(
            keywords,
            time_range_days,
            output_dir=campaign_dir,
            keyword_label=service or brand,
            industry=industry or None,
        )
    else:
        print("  已略過 Dcard。")

    # --- 第二階段：PTT ---
    print("\n【第二階段】PTT 輿情搜尋")
    run_ptt = input("  是否執行 PTT？(y/n，預設 y)：").strip().lower() != "n"
    time_years = 1
    if run_ptt:
        from ptt_scraper import run_ptt_scrape
        # 以第一個關鍵字或服務名搜尋 PTT（避免多關鍵字耗時過長）
        ptt_kw = keywords[0] if keywords else (service or brand)
        run_ptt_scrape(ptt_kw, time_years=time_years, output_dir=campaign_dir)
    else:
        print("  已略過 PTT。")

    print("\n" + "=" * 60)
    print(f"  全部完成。所有報表位於：{campaign_dir}")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    run()
# -*- coding: utf-8 -*-
"""
市調流程整合 V2.0：加入關鍵字確認機制
"""

import json
import os
import sys

try:
    from output_utils import get_campaign_output_dir
    from keyword_validator import run_keyword_validation  # 新增
except ImportError:
    print("⚠️ 請確保 keyword_validator.py 在同一目錄")
    sys.exit(1)

def main():
    print("="*60)
    print("🎯 競品輿情分析系統 V2.0")
    print("="*60)
    
    # === 第一步：基本資訊輸入 ===
    brand = input("\n請輸入自有品牌名稱：").strip()
    entity_type = input("品牌型態（例：個人品牌/公司/產品）：").strip() or "品牌"
    service = input("核心產品/服務（例：約會課程）：").strip()
    industry = input("所屬產業（例：教育培訓）：").strip()
    
    # === 第二步：建立輸出資料夾 ===
    campaign_dir = get_campaign_output_dir()
    print(f"\n📁 本次分析資料夾：{campaign_dir}")
    
    # === 第三步：競品雷達掃描 ===
    print("\n" + "="*60)
    print("階段一：競品雷達掃描")
    print("="*60)
    
    from auto_competitor_finder import run_competitor_analysis
    competitors_file = run_competitor_analysis(
        brand, entity_type, service, industry, campaign_dir
    )
    
    # 讀取競品資料
    with open(competitors_file, 'r', encoding='utf-8') as f:
        comp_data = json.load(f)
    
    competitor_names = [c.get('name', '') for c in comp_data if c.get('name')]
    
    # === 🆕 第四步：關鍵字確認機制 ===
    print("\n" + "="*60)
    print("階段二：關鍵字確認與優化")
    print("="*60)
    
    api_key = os.getenv("GEMINI_API_KEY") or "你的API金鑰"
    
    keywords_file = run_keyword_validation(
        brand=brand,
        competitors=competitor_names,
        industry=industry,
        service=service,
        api_key=api_key,
        output_dir=campaign_dir
    )
    
    # 讀取確認後的關鍵字
    with open(keywords_file, 'r', encoding='utf-8') as f:
        keywords_data = json.load(f)
    
    # 合併所有類別的關鍵字
    all_keywords = []
    for category_keywords in keywords_data['keywords'].values():
        all_keywords.extend(category_keywords)
    
    print(f"\n✅ 將使用 {len(all_keywords)} 個關鍵字進行輿情搜尋")
    
    # === 第五步：Dcard 輿情分析 ===
    print("\n" + "="*60)
    print("階段三：Dcard 輿情分析")
    print("="*60)
    
    try:
        from dcard_scraper import scrape_dcard_with_keywords
        dcard_csv = scrape_dcard_with_keywords(
            keywords=all_keywords,
            output_dir=campaign_dir,
            max_days=180  # 可改為使用者輸入
        )
        print(f"✅ Dcard 分析完成：{dcard_csv}")
    except Exception as e:
        print(f"⚠️ Dcard 分析失敗：{e}")
    
    # === 第六步：PTT 輿情分析 ===
    print("\n" + "="*60)
    print("階段四：PTT 輿情分析")
    print("="*60)
    
    try:
        from ptt_scraper import scrape_ptt_with_keywords
        ptt_csv = scrape_ptt_with_keywords(
            keywords=all_keywords,
            output_dir=campaign_dir,
            years=1  # 可改為使用者輸入
        )
        print(f"✅ PTT 分析完成：{ptt_csv}")
    except Exception as e:
        print(f"⚠️ PTT 分析失敗：{e}")
    
    # === 第七步：生成最終報告 ===
    print("\n" + "="*60)
    print("階段五：生成整合報告")
    print("="*60)
    
    # （下一步會實作）
    print("⏳ 報告生成功能開發中...")
    
    print("\n" + "="*60)
    print(f"✅ 所有分析完成！結果已儲存至：{campaign_dir}")
    print("="*60)

if __name__ == "__main__":
    main()
