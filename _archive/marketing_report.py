# -*- coding: utf-8 -*-
"""
行銷專家版最終報告生成器
包含：執行摘要、SWOT分析、行動建議、數據視覺化建議
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

class MarketingReportGenerator:
    """行銷專家版報告生成器"""
    
    def __init__(self, campaign_dir: str):
        self.campaign_dir = Path(campaign_dir)
        self.data = {}
        
    def load_all_data(self):
        """載入所有數據"""
        # 載入專案配置
        config_file = self.campaign_dir / "project_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self.data['config'] = json.load(f)
        
        # 載入競品資料
        competitors_file = self.campaign_dir / "competitors.json"
        if competitors_file.exists():
            with open(competitors_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self.data['competitors'] = raw.get('competitors', raw) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        
        # 載入關鍵字
        keywords_file = self.campaign_dir / "confirmed_keywords.json"
        if keywords_file.exists():
            with open(keywords_file, 'r', encoding='utf-8') as f:
                self.data['keywords'] = json.load(f)
        
        # 載入輿情數據
        dcard_files = list(self.campaign_dir.glob("dcard_*.csv"))
        if dcard_files:
            self.data['dcard_df'] = pd.read_csv(dcard_files[0])
        
        ptt_files = list(self.campaign_dir.glob("ptt_*.csv"))
        if ptt_files:
            self.data['ptt_df'] = pd.read_csv(ptt_files[0])
        
        # 載入情緒分析
        sentiment_files = list(self.campaign_dir.glob("*_sentiment_*.json"))
        if sentiment_files:
            with open(sentiment_files[0], 'r', encoding='utf-8') as f:
                self.data['sentiment'] = json.load(f)
    
    def generate_executive_summary(self) -> Dict:
        """生成執行摘要"""
        config = self.data.get('config', {})
        competitors = self.data.get('competitors', [])
        
        # 計算關鍵指標
        total_competitors = len(competitors)
        high_end_count = len([c for c in competitors if isinstance(c, dict) and 
                             ('高價' in str(c.get('label', '')) or '高端' in str(c.get('label', '')))])
        
        # 輿情分析
        sentiment_data = self.data.get('sentiment', {})
        anger_index = sentiment_data.get('anger_index', 0)
        
        return {
            "品牌名稱": config.get('brand', '未知'),
            "調查日期": datetime.now().strftime('%Y年%m月%d日'),
            "產業類別": config.get('industry', '未知'),
            "競品數量": total_competitors,
            "高端競品比例": f"{high_end_count/total_competitors*100:.1f}%" if total_competitors > 0 else "0%",
            "市場憤怒指數": f"{anger_index:.1f}%" if anger_index else "未分析",
            "主要發現": self._generate_key_findings(),
            "建議策略": self._generate_strategy_recommendation()
        }
    
    def _generate_key_findings(self) -> str:
        """生成主要發現"""
        competitors = self.data.get('competitors', [])
        config = self.data.get('config', {})
        
        findings = []
        
        # 市場競爭程度
        if len(competitors) >= 8:
            findings.append("市場競爭激烈，進入門檻較高")
        elif len(competitors) >= 3:
            findings.append("市場有一定競爭，但仍有發展空間")
        else:
            findings.append("市場相對藍海，機會較多")
        
        # 價格帶分析
        price_ranges = [c.get('price_range', '') for c in competitors if isinstance(c, dict)]
        high_price_count = sum(1 for p in price_ranges if '高' in str(p) or 'NT$' in str(p) and int(str(p).replace('NT$', '').replace(',', '').split('-')[0]) > 5000)
        
        if high_price_count > len(competitors) * 0.5:
            findings.append("市場以高端產品為主，價格敏感度較低")
        else:
            findings.append("市場價格帶分散，需明確定位")
        
        # 輿情情緒
        sentiment = self.data.get('sentiment', {})
        if sentiment.get('anger_index', 0) > 30:
            findings.append("市場負面情緒較高，需注意口碑管理")
        elif sentiment.get('anger_index', 0) < 10:
            findings.append("市場情緒相對正面，機會良好")
        
        return "；".join(findings)
    
    def _generate_strategy_recommendation(self) -> str:
        """生成策略建議"""
        competitors = self.data.get('competitors', [])
        
        if len(competitors) == 0:
            return "建議進行市場教育，建立品牌認知"
        
        # 分析競品類型
        labels = [c.get('label', '') for c in competitors if isinstance(c, dict)]
        
        if any('高價' in str(l) or '高端' in str(l) for l in labels):
            return "建議採取差異化定位，避開高端市場直接競爭"
        elif any('平價' in str(l) or '低價' in str(l) for l in labels):
            return "建議提升產品價值，避免陷入價格戰"
        else:
            return "建議建立獨特價值主張，創造市場區隔"
    
    def generate_swot_analysis(self) -> Dict:
        """生成 SWOT 分析"""
        config = self.data.get('config', {})
        competitors = self.data.get('competitors', [])
        
        return {
            "優勢 (Strengths)": [
                "完整的市場數據分析能力",
                "AI驅動的深度洞察",
                "多平台輿情監控",
                "即時競爭情報"
            ],
            "劣勢 (Weaknesses)": [
                "新品牌市場認知度不足",
                "資源有限需精準投放",
                "需建立品牌信任度"
            ],
            "機會 (Opportunities)": [
                "市場數位化轉型需求",
                "數據驅動決策趨勢",
                "AI工具普及化",
                "遠距工作常態化"
            ],
            "威脅 (Threats)": [
                "現有競品市場佔有率高",
                "技術門檻降低競爭加劇",
                "經濟環境不確定性",
                "法規政策變化"
            ]
        }
    
    def generate_actionable_insights(self) -> Dict[str, List[str]]:
        """生成行動建議"""
        return {
            "短期策略 (1-3個月)": [
                "優化官網SEO，針對高搜尋量關鍵字",
                "建立內容行銷策略，產出產業洞察報告",
                "進行競品定價分析，調整價格策略",
                "啟動社群媒體監測，掌握市場聲量"
            ],
            "中期策略 (3-6個月)": [
                "開發差異化產品功能，建立技術壁壘",
                "建立合作夥伴生態系，拓展市場觸及",
                "進行A/B測試，優化轉換漏斗",
                "建立品牌故事與內容資產"
            ],
            "長期策略 (6-12個月)": [
                "考慮市場擴張至相關產業",
                "建立數據分析平台，提供SaaS服務",
                "發展品牌生態系，提高用戶黏著度",
                "探索國際市場機會"
            ]
        }
    
    def generate_visualization_recommendations(self) -> List[str]:
        """生成數據視覺化建議"""
        return [
            "競品雷達圖：價格、聲量、口碑、技術、通路五維度對比",
            "市場定位矩陣：價格 vs. 品質二維定位圖",
            "情緒趨勢圖：輿情情緒隨時間變化趨勢",
            "關鍵字熱力圖：高搜尋量關鍵字視覺化",
            "競品社群影響力圖：各平台粉絲數與互動率對比",
            "價格帶分布圖：競品價格區間視覺化",
            "SWOT分析圖：視覺化優勢劣勢機會威脅",
            "市場佔有率圖：競品市場份額估算"
        ]
    
    def generate_marketing_report(self) -> str:
        """生成完整行銷報告"""
        self.load_all_data()
        
        executive_summary = self.generate_executive_summary()
        swot_analysis = self.generate_swot_analysis()
        actionable_insights = self.generate_actionable_insights()
        viz_recommendations = self.generate_visualization_recommendations()
        
        report = f"""# 🎯 市場調查報告（行銷專家版）

## 📊 執行摘要 (Executive Summary)

"""
        
        for key, value in executive_summary.items():
            report += f"- **{key}**：{value}\n"
        
        report += f"""
## ⚔️ SWOT 分析

### 優勢 (Strengths)
"""
        for strength in swot_analysis["優勢 (Strengths)"]:
            report += f"- ✅ {strength}\n"
        
        report += f"""
### 劣勢 (Weaknesses)
"""
        for weakness in swot_analysis["劣勢 (Weaknesses)"]:
            report += f"- ⚠️ {weakness}\n"
        
        report += f"""
### 機會 (Opportunities)
"""
        for opportunity in swot_analysis["機會 (Opportunities)"]:
            report += f"- 🚀 {opportunity}\n"
        
        report += f"""
### 威脅 (Threats)
"""
        for threat in swot_analysis["威脅 (Threats)"]:
            report += f"- ⚠️ {threat}\n"
        
        report += f"""
## 🎯 行動建議 (Actionable Insights)

### 短期策略 (1-3個月)
"""
        for insight in actionable_insights["短期策略 (1-3個月)"]:
            report += f"- 📅 {insight}\n"
        
        report += f"""
### 中期策略 (3-6個月)
"""
        for insight in actionable_insights["中期策略 (3-6個月)"]:
            report += f"- 📈 {insight}\n"
        
        report += f"""
### 長期策略 (6-12個月)
"""
        for insight in actionable_insights["長期策略 (6-12個月)"]:
            report += f"- 🌟 {insight}\n"
        
        report += f"""
## 📈 數據視覺化建議

建議製作以下圖表以提升報告說服力：
"""
        for i, viz in enumerate(viz_recommendations, 1):
            report += f"{i}. {viz}\n"
        
        report += f"""
## 📋 附錄：分析數據來源

1. **競品分析**：{len(self.data.get('competitors', []))} 個競品資料
2. **輿情分析**：Dcard {len(self.data.get('dcard_df', [])) if 'dcard_df' in self.data else 0} 篇，PTT {len(self.data.get('ptt_df', [])) if 'ptt_df' in self.data else 0} 篇
3. **關鍵字分析**：{len(self.data.get('keywords', {}).get('keywords', [])) if isinstance(self.data.get('keywords'), dict) else 0} 個驗證關鍵字
4. **情緒分析**：市場憤怒指數 {self.data.get('sentiment', {}).get('anger_index', 0):.1f}%

---
*報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*MKTBrs 行銷專家分析系統 v2.0*
"""
        
        return report
    
    def save_report(self, filename: str = "FINAL_MARKETING_REPORT.md") -> str:
        """儲存報告"""
        report_content = self.generate_marketing_report()
        report_path = self.campaign_dir / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(report_path)

# 簡化使用
def generate_marketing_report(campaign_dir: str) -> str:
    """快速生成行銷報告"""
    generator = MarketingReportGenerator(campaign_dir)
    return generator.save_report()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        campaign_dir = sys.argv[1]
        report_path = generate_marketing_report(campaign_dir)
        print(f"✅ 行銷報告已生成：{report_path}")
    else:
        print("請指定 campaign 資料夾路徑")
        print("用法：python marketing_report.py <campaign_dir>")