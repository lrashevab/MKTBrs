# -*- coding: utf-8 -*-
"""
報告生成器：整合所有數據，產出專業報告
支援格式：Markdown、HTML、PDF、PowerPoint
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import pandas as pd  # type: ignore[reportMissingImports]

from config import Config
from logger import get_logger

logger = get_logger("report_generator")

class ReportGenerator:
    """報告生成器"""
    
    def __init__(self, campaign_dir: str):
        self.campaign_dir = Path(campaign_dir)
        self.data = {}
        
    def load_all_data(self):
        """載入所有階段的數據"""
        logger.info("📂 載入分析數據...")
        
        # 載入專案配置
        config_file = self.campaign_dir / "project_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self.data['config'] = json.load(f)
        
        # 載入競品資料（相容 {competitors: [...]} 或純陣列）
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
        
        # 載入 Dcard 數據
        dcard_files = list(self.campaign_dir.glob("dcard_*.csv"))
        if dcard_files:
            self.data['dcard_df'] = pd.read_csv(dcard_files[0])
        
        # 載入 PTT 數據
        ptt_files = list(self.campaign_dir.glob("ptt_*.csv"))
        if ptt_files:
            self.data['ptt_df'] = pd.read_csv(ptt_files[0])
        
        logger.info(f"✅ 已載入 {len(self.data)} 個數據源")
        
    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式報告"""
        logger.info("📝 生成 Markdown 報告...")
        
        config = self.data.get('config', {})
        competitors = self.data.get('competitors', [])
        keywords = self.data.get('keywords', {})
        
        report = f"""# 市場調查報告

**品牌名稱**：{config.get('brand', '未知')}  
**調查日期**：{datetime.now().strftime('%Y年%m月%d日')}  
**調查目的**：{config.get('purpose', '綜合調查')}  
**產業別**：{config.get('industry', '未知')}  
**核心服務**：{config.get('service', '未知')}

---

## 📊 執行摘要

### 調查範圍
- **競品數量**：{len(competitors)} 個
- **關鍵字數量**：{keywords.get('total_count', 0)} 個
- **Dcard 文章**：{len(self.data.get('dcard_df', [])) if 'dcard_df' in self.data else 0} 篇
- **PTT 文章**：{len(self.data.get('ptt_df', [])) if 'ptt_df' in self.data else 0} 篇

### 主要發現
1. **市場規模**：（待補充產業掃描數據）
2. **競爭態勢**：找到 {len(competitors)} 個直接競品，其中 {len([c for c in competitors if isinstance(c, dict) and (str(c.get('label', '') or c.get('tags', '')).find('高價') >= 0)])} 個定位高端市場
3. **消費者痛點**：（待補充輿情分析）

---

## 🎯 競品分析

"""
        
        # 競品詳細資訊（相容 competitor_name/label/fan_profile/keywords 與舊欄位）
        for i, comp in enumerate((competitors or [])[:10], 1):
            name = comp.get('competitor_name', comp.get('name', '未知'))
            label = comp.get('label', comp.get('tags', '未知'))
            report += f"""
### {i}. {name}

| 項目 | 內容 |
|------|------|
| **標籤** | {label} |
| **來源** | {comp.get('verification_info', comp.get('positioning', '未知'))} |
| **目標客群** | {comp.get('fan_profile', '未知')} |

**關鍵字**：{', '.join(comp.get('keywords', []) or [])}

---
"""
        
        # 關鍵字分析
        report += """
## 🔑 關鍵字策略

"""
        
        if keywords:
            kw_data = keywords.get('keywords', {})
            report += f"""
### 關鍵字分類

**品牌直稱類** ({len(kw_data.get('brand_direct', []))} 個)：
{', '.join(kw_data.get('brand_direct', []))}

**產品功能類** ({len(kw_data.get('product_function', []))} 個)：
{', '.join(kw_data.get('product_function', []))}

**情境討論類** ({len(kw_data.get('context_discussion', []))} 個)：
{', '.join(kw_data.get('context_discussion', []))}

"""
        
        # 輿情分析
        report += """
---

## 💬 社群輿情分析

"""
        
        if 'dcard_df' in self.data:
            dcard_df = self.data['dcard_df']
            report += f"""
### Dcard 分析

- **總文章數**：{len(dcard_df)} 篇
- **平均互動指數**：{dcard_df['互動指數'].mean():.1f} 
- **最熱門看板**：{dcard_df['看板'].mode()[0] if not dcard_df.empty else '無'}

**高互動文章 TOP 5**：

"""
            top_articles = dcard_df.nlargest(5, '互動指數')[['標題', '互動指數', '看板']]
            for idx, row in top_articles.iterrows():
                report += f"- [{row['看板']}] {row['標題']} (互動: {row['互動指數']})\n"
        
        if 'ptt_df' in self.data:
            ptt_df = self.data['ptt_df']
            report += f"""

### PTT 分析

- **總文章數**：{len(ptt_df)} 篇
- **平均推文數**：{ptt_df['推文數'].mean():.1f} 
- **最熱門看板**：{ptt_df['看板'].mode()[0] if not ptt_df.empty else '無'}

"""
        
        # 結論與建議
        report += """
---

## 💡 行銷策略建議

### 一、市場切入點

（此處應整合 Gemini 深度分析結果）

### 二、內容行銷方向

基於輿情分析，建議主打以下主題：
1. （待補充）
2. （待補充）
3. （待補充）

### 三、預算分配建議

| 項目 | 預算佔比 | 說明 |
|------|---------|------|
| 社群廣告 | 40% | Dcard、PTT 置頂文 |
| KOL 合作 | 30% | 微網紅策略 |
| 內容製作 | 20% | 圖文、影片 |
| 數據分析 | 10% | 持續監控 |

---

## 📎 附錄

### 原始數據檔案

"""
        
        # 列出所有檔案
        for file in self.campaign_dir.glob("*"):
            if file.is_file():
                report += f"- `{file.name}`\n"
        
        report += f"""

---

**報告生成時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**系統版本**：V2.0
"""
        
        # 儲存報告
        output_file = self.campaign_dir / "FINAL_REPORT.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ Markdown 報告已生成：{output_file}")
        return str(output_file)
    
    def generate_html_report(self, md_file: str) -> str:
        """將 Markdown 轉換為 HTML"""
        try:
            import markdown  # type: ignore[reportMissingImports, reportMissingModuleSource]

            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市場調查報告</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.8;
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 40px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
{markdown.markdown(md_content, extensions=['tables', 'fenced_code'])}
</body>
</html>
"""
            
            html_file = Path(md_file).with_suffix('.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ HTML 報告已生成：{html_file}")
            return str(html_file)
            
        except ImportError:
            logger.warning("⚠️ 請安裝 markdown 套件：pip install markdown")
            return ""
    
    def generate_pdf_report(self, html_file: str) -> str:
        """將 HTML 轉換為 PDF"""
        try:
            import pdfkit  # type: ignore[reportMissingImports]

            pdf_file = Path(html_file).with_suffix('.pdf')
            pdfkit.from_file(html_file, str(pdf_file))
            
            logger.info(f"✅ PDF 報告已生成：{pdf_file}")
            return str(pdf_file)
            
        except Exception as e:
            logger.warning(f"⚠️ PDF 生成失敗：{e}")
            logger.info("提示：請安裝 wkhtmltopdf 工具")
            return ""
    
    def generate_all_formats(self) -> Dict[str, str]:
        """生成所有格式的報告"""
        self.load_all_data()
        
        outputs = {}
        
        # Markdown
        md_file = self.generate_markdown_report()
        outputs['markdown'] = md_file
        
        # HTML
        html_file = self.generate_html_report(md_file)
        if html_file:
            outputs['html'] = html_file
        
        # PDF
        if html_file:
            pdf_file = self.generate_pdf_report(html_file)
            if pdf_file:
                outputs['pdf'] = pdf_file
        
        return outputs


def generate_final_report(campaign_dir: str) -> Dict[str, str]:
    """便捷函式：生成最終報告"""
    generator = ReportGenerator(campaign_dir)
    return generator.generate_all_formats()
