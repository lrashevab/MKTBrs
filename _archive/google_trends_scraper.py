# -*- coding: utf-8 -*-
"""
Google Trends 搜尋聲量爬蟲
透過 pytrends 抓取台灣地區 12 個月搜尋趨勢，計算品牌 Share of Search。

主要函式：
    run_google_trends_scrape(brand, competitors, output_dir, ...) -> (dict, str)

輸出 google_trends.json：
    {
        "brand": "品牌名",
        "keywords": ["品牌", "競品A", "競品B", ...],
        "share_of_search": {"品牌": 42.3, "競品A": 31.1, ...},
        "recent_3m_avg": {"品牌": 68, "競品A": 45, ...},
        "weekly_trends": {"品牌": [{"date":"2024-01-07","value":72}, ...], ...},
        "scraped_at": "2024-03-01T10:30:00"
    }
"""

import json
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    from pytrends.request import TrendReq
    from pytrends.exceptions import ResponseError
    _PYTRENDS_OK = True
except ImportError:
    _PYTRENDS_OK = False


# ── 公開入口 ──────────────────────────────────────────────────

def run_google_trends_scrape(
    brand: str,
    competitors: List[str],
    output_dir: str,
    timeframe: str = 'today 12-m',
    geo: str = 'TW',
) -> Tuple[Optional[dict], Optional[str]]:
    """
    抓取品牌與競品的 Google 搜尋趨勢，計算 Share of Search。

    Args:
        brand           — 自有品牌名稱
        competitors     — 競品名稱清單（最多取前 4 個）
        output_dir      — campaign 資料夾路徑
        timeframe       — 搜尋時間範圍（pytrends 格式，預設一年）
        geo             — 地區代碼，預設台灣 'TW'

    Returns:
        (trends_data, output_path)
        失敗時回傳 (None, None)
    """
    if not _PYTRENDS_OK:
        print("⚠️ pytrends 未安裝，跳過 Google Trends 分析。請執行：pip install pytrends")
        return None, None

    if not brand:
        print("⚠️ 未提供品牌名稱，跳過 Google Trends 分析。")
        return None, None

    # 最多比較 5 個關鍵字（Google Trends 限制）
    kw_list = [brand] + [c for c in competitors if c][:4]
    kw_list = list(dict.fromkeys(kw_list))  # 去重，保持順序

    print(f"  → Google Trends 分析關鍵字：{', '.join(kw_list)}")

    trends_data = _fetch_trends(kw_list, timeframe, geo)
    if trends_data is None:
        return None, None

    trends_data['brand'] = brand
    trends_data['keywords'] = kw_list
    trends_data['scraped_at'] = datetime.now().isoformat()

    output_path = os.path.join(output_dir, "google_trends.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(trends_data, f, ensure_ascii=False, indent=2)

    return trends_data, output_path


# ── 內部：抓取與解析 ─────────────────────────────────────────

def _fetch_trends(
    kw_list: List[str],
    timeframe: str,
    geo: str,
) -> Optional[Dict]:
    """呼叫 pytrends API，回傳 trends_data dict，失敗回傳 None。"""
    try:
        pytrends = TrendReq(hl='zh-TW', tz=480, timeout=(10, 25))

        # 若關鍵字超過 5 個，分批處理後合併（以第一批為基準）
        if len(kw_list) <= 5:
            batches = [kw_list]
        else:
            # 每批以 brand 為錨點做相對比較
            brand = kw_list[0]
            batches = [
                [brand] + kw_list[1:5],
                [brand] + kw_list[5:9],
            ]

        combined: Dict[str, list] = {}
        for batch in batches:
            _sleep()
            batch_data = _fetch_batch(pytrends, batch, timeframe, geo)
            if batch_data is None:
                continue
            for kw, series in batch_data.items():
                if kw not in combined:
                    combined[kw] = series

        if not combined:
            return None

        return _build_result(combined)

    except Exception as e:
        print(f"⚠️ Google Trends 失敗：{e}")
        return None


def _fetch_batch(
    pytrends: 'TrendReq',
    kw_list: List[str],
    timeframe: str,
    geo: str,
) -> Optional[Dict[str, list]]:
    """單批抓取，回傳 {keyword: [{date, value}, ...]}，失敗回傳 None。"""
    try:
        pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo=geo, gprop='')
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            return None

        result = {}
        for kw in kw_list:
            if kw not in df.columns:
                continue
            result[kw] = [
                {"date": str(idx.date()), "value": int(row[kw])}
                for idx, row in df.iterrows()
                if not row.get('isPartial', False)
            ]
        return result if result else None

    except ResponseError as e:
        print(f"⚠️ Google Trends 速率限制：{e}")
        return None
    except Exception as e:
        print(f"⚠️ Google Trends 批次抓取失敗：{e}")
        return None


def _build_result(combined: Dict[str, list]) -> Dict:
    """從原始週趨勢計算 Share of Search 和近 3 個月平均。"""
    # Share of Search：各關鍵字平均搜尋量 / 總量 × 100
    averages: Dict[str, float] = {}
    for kw, series in combined.items():
        vals = [p['value'] for p in series if p['value'] > 0]
        averages[kw] = sum(vals) / len(vals) if vals else 0.0

    total_avg = sum(averages.values())
    share_of_search: Dict[str, float] = {}
    if total_avg > 0:
        share_of_search = {
            kw: round(avg / total_avg * 100, 1)
            for kw, avg in averages.items()
        }
    else:
        share_of_search = {kw: 0.0 for kw in averages}

    # 近 3 個月平均（最新 13 週）
    recent_3m_avg: Dict[str, float] = {}
    for kw, series in combined.items():
        recent = [p['value'] for p in series[-13:] if p['value'] > 0]
        recent_3m_avg[kw] = round(sum(recent) / len(recent), 1) if recent else 0.0

    return {
        'share_of_search': share_of_search,
        'recent_3m_avg': recent_3m_avg,
        'weekly_trends': combined,
    }


def _sleep() -> None:
    """在請求間加入隨機延遲，避免觸發 Google Trends 速率限制。"""
    time.sleep(random.uniform(1.5, 3.5))


# ── 獨立執行測試 ──────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    import tempfile

    brand = sys.argv[1] if len(sys.argv) > 1 else '品牌A'
    competitors_raw = sys.argv[2] if len(sys.argv) > 2 else '品牌B,品牌C'
    competitors = [c.strip() for c in competitors_raw.split(',') if c.strip()]

    with tempfile.TemporaryDirectory() as tmpdir:
        data, path = run_google_trends_scrape(brand, competitors, tmpdir)
        if data:
            print(f"\nShare of Search: {data['share_of_search']}")
            print(f"近 3 個月平均:    {data['recent_3m_avg']}")
            print(f"輸出路徑:         {path}")
        else:
            print("Google Trends 抓取失敗或無資料。")
