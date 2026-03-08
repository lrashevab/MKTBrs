# -*- coding: utf-8 -*-
"""
競品量化評分矩陣（Competitive Scorecard）
從現有 campaign 資料夾的各類輸出檔案中，自動計算品牌與競品的 6 維度評分（0–5 分）。

使用方式：
    from competitive_scorecard import CompetitiveScorecard
    sc = CompetitiveScorecard(campaign_dir)
    data = sc.calculate(brand, competitors)

輸出 competitive_scorecard.json：
    {
        "brand": "品牌名",
        "competitors": ["競品A", "競品B", ...],
        "dimensions": ["Google搜尋熱度", "社群提及熱度", "情緒健康度",
                        "媒體能見度", "AI競爭定位", "AI產品廣度"],
        "scores": {
            "品牌名":  {"Google搜尋熱度": 4.2, "社群提及熱度": 3.1, ...},
            "競品A":   {"Google搜尋熱度": 3.5, ...},
            ...
        },
        "data_sources": {
            "Google搜尋熱度": "google_trends.json",
            "社群提及熱度":   "所有 CSV 全文比對",
            ...
        },
        "generated_at": "2024-03-01T10:30:00"
    }
"""

import csv
import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── 維度定義 ────────────────────────────────────────────────

DIMENSIONS = [
    "Google搜尋熱度",
    "社群提及熱度",
    "情緒健康度",
    "媒體能見度",
    "AI競爭定位",
    "AI產品廣度",
]

DATA_SOURCES = {
    "Google搜尋熱度": "google_trends.json（Share of Search）",
    "社群提及熱度":   "Dcard/PTT/Threads CSV 全文品牌名稱出現次數",
    "情緒健康度":     "Dcard/PTT sentiment JSON（anger_index 反轉）",
    "媒體能見度":     "Google News CSV 標題包含品牌名稱次數",
    "AI競爭定位":     "competitors.json（市場地位 + 定價層級）",
    "AI產品廣度":     "stage5_deep_analysis.md（強項條目數）",
}


class CompetitiveScorecard:
    """從現有 campaign 輸出資料計算競品量化評分矩陣。"""

    def __init__(self, campaign_dir: str):
        self.campaign_dir = Path(campaign_dir)

    def calculate(
        self,
        brand: str,
        competitors: List[str],
    ) -> dict:
        """
        計算品牌與競品的 6 維度評分，並儲存 competitive_scorecard.json。

        Args:
            brand       — 自有品牌名稱
            competitors — 競品名稱清單

        Returns:
            scorecard dict（同時寫入 competitive_scorecard.json）
        """
        all_names = [brand] + [c for c in competitors if c]

        # 逐維度計算原始分數
        raw = {name: {} for name in all_names}

        self._score_google_trends(raw, all_names)
        self._score_social_mentions(raw, all_names)
        self._score_emotional_health(raw, all_names, brand)
        self._score_media_visibility(raw, all_names)
        self._score_ai_positioning(raw, all_names)
        self._score_ai_product_breadth(raw, all_names)

        # 正規化到 0–5 分
        scores = self._normalize(raw, all_names)

        result = {
            "brand":        brand,
            "competitors":  competitors,
            "dimensions":   DIMENSIONS,
            "scores":       scores,
            "data_sources": DATA_SOURCES,
            "generated_at": datetime.now().isoformat(),
        }

        out_path = self.campaign_dir / "competitive_scorecard.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    # ── 維度 1：Google 搜尋熱度 ──────────────────────────────

    def _score_google_trends(self, raw: dict, names: List[str]) -> None:
        """從 google_trends.json 取 Share of Search（0–100），直接當原始分。"""
        trends_path = self.campaign_dir / "google_trends.json"
        key = "Google搜尋熱度"
        if not trends_path.exists():
            for name in names:
                raw[name][key] = None  # 資料不存在，標示為 N/A
            return

        try:
            with open(trends_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            sos: Dict[str, float] = data.get('share_of_search', {})
            for name in names:
                # 嘗試名稱完全比對，再試包含比對
                val = sos.get(name)
                if val is None:
                    for k, v in sos.items():
                        if name in k or k in name:
                            val = v
                            break
                raw[name][key] = float(val) if val is not None else 0.0
        except Exception:
            for name in names:
                raw[name][key] = 0.0

    # ── 維度 2：社群提及熱度 ─────────────────────────────────

    def _score_social_mentions(self, raw: dict, names: List[str]) -> None:
        """掃描所有 Dcard/PTT/Threads CSV 的標題+內文，計算品牌名出現次數。"""
        key = "社群提及熱度"
        counts = {name: 0 for name in names}

        csv_patterns = [
            "dcard_*.csv", "ptt_*.csv", "threads_*.csv",
        ]
        for pattern in csv_patterns:
            for csv_path in self.campaign_dir.glob(pattern):
                try:
                    with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            text = ' '.join(row).lower()
                            for name in names:
                                if name and name.lower() in text:
                                    counts[name] += 1
                except Exception:
                    continue

        for name in names:
            raw[name][key] = float(counts[name])

    # ── 維度 3：情緒健康度 ──────────────────────────────────

    def _score_emotional_health(
        self, raw: dict, names: List[str], brand: str
    ) -> None:
        """
        從 Dcard/PTT sentiment JSON 取 anger_index，轉換為健康度（100 - anger）。
        競品若無獨立輿情資料，改用 CSV 中負面詞比例估算。
        """
        key = "情緒健康度"

        # 品牌：從 sentiment JSON 取
        brand_health = self._read_sentiment_health(brand)
        raw[brand][key] = brand_health

        # 競品：讀全部 CSV，估算負面詞占比
        try:
            from sentiment_config import get_negative_words
            neg_words = get_negative_words()
        except ImportError:
            neg_words = ["雷", "爛", "騙", "失望"]

        for name in names:
            if name == brand:
                continue
            health = self._estimate_competitor_health(name, neg_words)
            raw[name][key] = health

    def _read_sentiment_health(self, brand: str) -> float:
        """讀取品牌的 Dcard/PTT sentiment JSON，取 anger_index 並轉為健康度。"""
        total_anger, count = 0.0, 0
        for pattern in ["dcard_sentiment_*.json", "ptt_sentiment_*.json"]:
            for path in self.campaign_dir.glob(pattern):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                    ai = d.get('anger_index', 50.0)
                    total_anger += float(ai)
                    count += 1
                except Exception:
                    continue
        avg_anger = total_anger / count if count > 0 else 50.0
        return max(0.0, 100.0 - avg_anger)

    def _estimate_competitor_health(
        self, name: str, neg_words: List[str]
    ) -> float:
        """從所有 CSV 估算競品的負面詞比例，轉換為健康度。"""
        total, neg_count = 0, 0
        for pattern in ["dcard_*.csv", "ptt_*.csv", "threads_*.csv"]:
            for csv_path in self.campaign_dir.glob(pattern):
                try:
                    with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            text = ' '.join(row)
                            if name.lower() not in text.lower():
                                continue
                            total += 1
                            if any(nw in text for nw in neg_words):
                                neg_count += 1
                except Exception:
                    continue
        if total == 0:
            return 50.0  # 無資料時給中間值
        anger = neg_count / total * 100
        return max(0.0, 100.0 - anger)

    # ── 維度 4：媒體能見度 ──────────────────────────────────

    def _score_media_visibility(self, raw: dict, names: List[str]) -> None:
        """計算 Google News CSV 標題中包含各品牌名稱的文章數。"""
        key = "媒體能見度"
        counts = {name: 0 for name in names}

        for csv_path in self.campaign_dir.glob("google_news_*.csv"):
            try:
                with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        title = (row.get('title') or row.get('標題') or '').lower()
                        summary = (row.get('summary') or row.get('摘要') or '').lower()
                        combined = title + ' ' + summary
                        for name in names:
                            if name and name.lower() in combined:
                                counts[name] += 1
            except Exception:
                continue

        for name in names:
            raw[name][key] = float(counts[name])

    # ── 維度 5：AI 競爭定位 ──────────────────────────────────

    def _score_ai_positioning(self, raw: dict, names: List[str]) -> None:
        """
        從 competitors.json 解析 pricing_tier 與 market_position，轉換為分數。
        品牌自身固定給 3.0（以競品相對定位為參考基準）。
        """
        key = "AI競爭定位"
        brand_name = names[0] if names else ''

        # 品牌：給基準分
        raw[brand_name][key] = 3.0

        comp_path = self.campaign_dir / "competitors.json"
        if not comp_path.exists():
            for name in names[1:]:
                raw[name][key] = 2.5
            return

        try:
            with open(comp_path, 'r', encoding='utf-8') as f:
                comp_data = json.load(f)
            comp_list = comp_data.get('competitors', comp_data) if isinstance(comp_data, dict) else comp_data
            if not isinstance(comp_list, list):
                comp_list = []

            # 建立名稱 → 競品資料的 lookup
            comp_lookup = {}
            for c in comp_list:
                cname = c.get('competitor_name') or c.get('name', '')
                if cname:
                    comp_lookup[cname] = c

            for name in names[1:]:
                comp = comp_lookup.get(name)
                if comp is None:
                    # 嘗試模糊比對
                    for k, v in comp_lookup.items():
                        if name in k or k in name:
                            comp = v
                            break
                raw[name][key] = self._positioning_to_score(comp) if comp else 2.5

        except Exception:
            for name in names[1:]:
                raw[name][key] = 2.5

    def _positioning_to_score(self, comp: dict) -> float:
        """根據 pricing_tier / market_position 欄位給分（0–5）。"""
        score = 2.5  # 預設中位

        # 定價層級加分
        tier = str(comp.get('pricing_tier', '') or comp.get('price_tier', '')).lower()
        if any(k in tier for k in ['premium', '高端', '高價', 'high']):
            score += 0.5
        elif any(k in tier for k in ['budget', '低價', '親民', 'low']):
            score -= 0.5

        # 市場地位加分（以正面詞計）
        position_text = str(
            comp.get('market_position', '') or
            comp.get('positioning', '') or
            comp.get('strengths', '')
        )
        positive_signals = ['領導', '第一', '龍頭', '知名', '領先', 'leader', '主流']
        negative_signals = ['新興', '小眾', '利基', '二線', 'niche']
        pos_hits = sum(1 for p in positive_signals if p in position_text)
        neg_hits = sum(1 for p in negative_signals if p in position_text)
        score += pos_hits * 0.3 - neg_hits * 0.2

        return max(0.0, min(5.0, score))

    # ── 維度 6：AI 產品廣度 ──────────────────────────────────

    def _score_ai_product_breadth(self, raw: dict, names: List[str]) -> None:
        """
        從 stage5_deep_analysis.md 解析各品牌強項條目數，作為產品廣度指標。
        """
        key = "AI產品廣度"
        md_path = self.campaign_dir / "stage5_deep_analysis.md"

        if not md_path.exists():
            for name in names:
                raw[name][key] = 2.5
            return

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
        except Exception:
            for name in names:
                raw[name][key] = 2.5
            return

        for name in names:
            count = self._count_strengths_in_md(name, md_text)
            raw[name][key] = float(count)

    def _count_strengths_in_md(self, name: str, md_text: str) -> int:
        """計算品牌名稱周圍出現「強項 / 優勢 / Strength」的條目數。"""
        # 找到品牌相關段落
        pattern = re.compile(
            rf'(?:###[^\n]*{re.escape(name)}[^\n]*\n)(.*?)(?=###|\Z)',
            re.DOTALL | re.IGNORECASE,
        )
        section = pattern.search(md_text)
        if not section:
            return 1  # 至少給 1

        section_text = section.group(1)

        # 尋找強項 / 優勢 / Strength 區塊後的列表項目數
        strength_block = re.search(
            r'(?:優勢|強項|Strength|S \(Strength)[^\n]*\n((?:[-*•]\s[^\n]+\n?)+)',
            section_text,
            re.IGNORECASE,
        )
        if strength_block:
            items = re.findall(r'^[-*•]\s', strength_block.group(1), re.MULTILINE)
            return max(1, len(items))

        # fallback：計算整個品牌段落的列表項目數
        all_items = re.findall(r'^[-*•]\s', section_text, re.MULTILINE)
        return max(1, len(all_items) // 2)  # 除以 2 以避免計入弱項

    # ── 正規化：原始分 → 0–5 分 ──────────────────────────────

    def _normalize(
        self, raw: dict, names: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        對每個維度，找到所有品牌中的最大值，等比縮放到 0–5 分。
        N/A（None）的維度標示為 -1（報告層渲染時顯示「資料不足」）。
        """
        scores: Dict[str, Dict[str, float]] = {name: {} for name in names}

        for dim in DIMENSIONS:
            vals = {
                name: raw[name].get(dim)
                for name in names
                if raw[name].get(dim) is not None
            }
            if not vals:
                for name in names:
                    scores[name][dim] = -1.0  # 資料不足
                continue

            max_val = max(vals.values()) or 1.0

            for name in names:
                raw_val = raw[name].get(dim)
                if raw_val is None:
                    scores[name][dim] = -1.0
                else:
                    scores[name][dim] = round(min(5.0, raw_val / max_val * 5.0), 2)

        return scores


# ── 獨立執行測試 ──────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法：python competitive_scorecard.py <campaign_dir> [brand] [競品A,競品B]")
        sys.exit(1)

    campaign_dir = sys.argv[1]
    brand = sys.argv[2] if len(sys.argv) > 2 else '品牌A'
    competitors = [c.strip() for c in sys.argv[3].split(',')] if len(sys.argv) > 3 else ['競品B', '競品C']

    sc = CompetitiveScorecard(campaign_dir)
    result = sc.calculate(brand, competitors)

    print(f"\n競品評分矩陣（0–5 分）：")
    print(f"{'':15}", end='')
    for dim in result['dimensions']:
        print(f"{dim[:8]:>10}", end='')
    print()
    for name, dim_scores in result['scores'].items():
        label = f"{'★ ' if name == brand else '  '}{name}"
        print(f"{label[:15]:15}", end='')
        for dim in result['dimensions']:
            val = dim_scores.get(dim, -1.0)
            print(f"{'N/A':>10}" if val < 0 else f"{val:>10.1f}", end='')
        print()
    print(f"\n結果已寫入：{campaign_dir}/competitive_scorecard.json")
