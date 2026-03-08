# -*- coding: utf-8 -*-
"""
V2 HTML 報告生成器：三種專業模板
- 執行摘要版 → report_executive_summary.html
- 競品對決版 → report_battlecard.html
- 深度分析版 → report_deep_analysis.html

使用方式：
    python html_report_generator.py <campaign_dir>

從 orchestrator 呼叫：
    from html_report_generator import generate_html_reports
    generate_html_reports(campaign_dir)
"""

import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Windows 終端機 UTF-8 輸出（避免 emoji 編碼錯誤）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


COMMON_CSS = """
/* ════════════════════════════════════════════
   DESIGN SYSTEM  ·  Version 3.0
   Philosophy: Apple clarity + McKinsey depth
   ════════════════════════════════════════════ */

:root {
  /* ── Brand Palette ── */
  --brand:       #0052CC;
  --brand-dark:  #003A99;
  --brand-mid:   #4A86D8;
  --brand-bg:    #EBF2FF;

  /* ── Semantic ── */
  --red:         #C9000A;
  --red-bg:      #FFF0F0;
  --green:       #1A7F37;
  --green-bg:    #EDFAF3;
  --amber:       #B45309;
  --amber-bg:    #FFFBEB;
  --purple:      #5C35CC;

  /* ── Ink Scale ── */
  --ink-1:       #111827;   /* headings */
  --ink-2:       #374151;   /* body      */
  --ink-3:       #6B7280;   /* secondary */
  --ink-4:       #9CA3AF;   /* muted     */

  /* ── Surface Scale ── */
  --bg:          #F3F4F8;
  --card:        #FFFFFF;
  --border:      #D1D5DB;
  --border-2:    #E9EBF0;

  /* ── Shadows ── */
  --s1: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --s2: 0 4px 14px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
  --s3: 0 12px 32px rgba(0,0,0,0.10), 0 4px 10px rgba(0,0,0,0.05);

  /* ── Radius ── */
  --r-xs: 4px;  --r-sm: 8px;  --r-md: 12px;  --r-lg: 18px;
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Base ── */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text',
                 'Helvetica Neue', 'Microsoft JhengHei', 'PingFang TC',
                 'Noto Sans TC', Arial, sans-serif;
    background: var(--bg);
    color: var(--ink-2);
    line-height: 1.65;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }

/* ════ HEADER ════ */
.report-header {
    background: linear-gradient(140deg, #060F1F 0%, #082248 40%, #0D3B8C 75%, #1558C8 100%);
    color: white;
    padding: 44px 48px;
    border-radius: var(--r-lg);
    margin-bottom: 26px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--s3);
}
.report-header::before {
    content: '';
    position: absolute; top: -80px; right: -60px;
    width: 320px; height: 320px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 70%);
    pointer-events: none;
}
.report-header::after {
    content: '';
    position: absolute; bottom: -60px; left: 30%;
    width: 240px; height: 240px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
    pointer-events: none;
}
.report-header h1 {
    font-size: 2.0rem; font-weight: 700; letter-spacing: -0.6px;
    margin-bottom: 8px; position: relative;
    text-shadow: 0 1px 4px rgba(0,0,0,0.25);
}
.report-header .subtitle {
    font-size: 0.92rem; opacity: 0.82; margin-top: 6px; position: relative;
}
.report-header .meta {
    margin-top: 18px; font-size: 0.76rem; opacity: 1; position: relative;
    display: flex; gap: 8px; flex-wrap: wrap;
}
.meta-pill {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.22);
    padding: 3px 12px; border-radius: 20px;
    backdrop-filter: blur(4px); white-space: nowrap;
}
.report-header-logo { max-height: 48px; margin-bottom: 12px; display: block; }

/* ════ KPI CARDS ════ */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 14px; margin-bottom: 24px;
}
.kpi-card {
    background: var(--card);
    border-radius: var(--r-md);
    padding: 22px 18px 18px;
    box-shadow: var(--s1);
    border: 1px solid var(--border-2);
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--brand-dark), var(--brand-mid));
}
.kpi-card::after {
    content: ''; position: absolute; bottom: -12px; right: -12px;
    width: 56px; height: 56px; border-radius: 50%;
    background: var(--brand-bg); opacity: 0.7;
}
.kpi-card .kpi-number {
    font-size: 3.1rem; font-weight: 700; color: var(--brand);
    line-height: 1; letter-spacing: -2px;
    font-variant-numeric: tabular-nums;
}
.kpi-card .kpi-label {
    font-size: 0.73rem; color: var(--ink-3); margin-top: 9px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.4px;
}

/* ════ SECTION CARDS ════ */
.section-card {
    background: var(--card);
    border-radius: var(--r-md);
    padding: 26px 28px;
    margin-bottom: 18px;
    box-shadow: var(--s1);
    border: 1px solid var(--border-2);
    transition: box-shadow 0.2s;
}
.section-card:hover { box-shadow: var(--s2); }
.section-card h2 {
    font-size: 1.0rem; font-weight: 600; color: var(--ink-1);
    margin-bottom: 18px; padding-bottom: 12px;
    border-bottom: 1px solid var(--border-2);
    display: flex; align-items: center; gap: 8px;
    letter-spacing: -0.1px;
}

/* ════ INSIGHT CALLOUT ════ */
.insight-callout {
    display: flex; align-items: flex-start; gap: 10px;
    background: var(--brand-bg);
    border-left: 3px solid var(--brand);
    border-radius: 0 var(--r-sm) var(--r-sm) 0;
    padding: 10px 14px; margin-top: 14px;
    font-size: 0.8rem; color: var(--brand-dark); line-height: 1.65;
}
.insight-callout strong { color: var(--brand-dark); font-weight: 600; }

/* ════ BAR CHART ════ */
.bar-chart { list-style: none; }
.bar-item { display: flex; align-items: center; margin-bottom: 10px; gap: 12px; }
.bar-label { width: 100px; font-size: 0.81rem; text-align: right; flex-shrink: 0; color: var(--ink-2); }
.bar-track { flex: 1; background: var(--border-2); border-radius: 6px; height: 22px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, var(--brand-dark), var(--brand-mid)); }
.bar-value { width: 58px; font-size: 0.8rem; color: var(--ink-3); font-weight: 500; }

/* ════ COMPETITOR CARDS ════ */
.competitor-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.competitor-card {
    border: 1px solid var(--border);
    border-radius: var(--r-sm); padding: 14px 16px;
    transition: box-shadow 0.2s, border-color 0.2s; background: var(--card);
}
.competitor-card:hover { box-shadow: var(--s2); border-color: var(--brand-mid); }
.competitor-card .comp-name { font-weight: 600; font-size: 0.92rem; color: var(--ink-1); }
.competitor-card .comp-label {
    font-size: 0.72rem; background: var(--brand-bg); color: var(--brand);
    padding: 2px 9px; border-radius: 12px; display: inline-block;
    margin: 5px 0 3px; font-weight: 500;
}
.competitor-card .comp-fan { font-size: 0.75rem; color: var(--ink-3); margin-top: 4px; }
.competitor-card .comp-kws { font-size: 0.7rem; color: var(--ink-4); margin-top: 6px; }

/* ════ RECOMMENDATIONS ════ */
.recommendation-item {
    display: flex; gap: 16px; padding: 15px 20px;
    border-radius: var(--r-sm); margin-bottom: 11px;
    background: #FAFBFF; border: 1px solid var(--border-2);
    border-left: 4px solid var(--brand); align-items: flex-start;
    transition: border-left-color 0.2s, box-shadow 0.2s;
}
.recommendation-item:hover {
    border-left-color: var(--brand-mid); box-shadow: var(--s1);
}
.rec-number {
    font-size: 1.3rem; font-weight: 800; color: var(--brand);
    min-width: 28px; line-height: 1.4; letter-spacing: -1px;
    font-variant-numeric: tabular-nums;
}
.rec-content { font-size: 0.87rem; line-height: 1.8; color: var(--ink-2); flex: 1; }

/* ════ ARTICLE TABLE ════ */
table.article-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.article-table th {
    background: var(--ink-1); color: white;
    padding: 10px 14px; text-align: left;
    font-weight: 600; font-size: 0.76rem; letter-spacing: 0.3px;
}
.article-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-2); vertical-align: middle; }
.article-table tbody tr:nth-child(even) td { background: #FAFBFD; }
.article-table tbody tr:hover td { background: var(--brand-bg); }
.article-table .engagement { font-weight: 600; color: var(--red); }
.article-link {
    color: var(--brand); text-decoration: none;
    border-bottom: 1px solid rgba(0,82,204,0.28);
    transition: color 0.15s, border-color 0.15s;
}
.article-link:hover { color: var(--red); border-bottom-color: var(--red); }
.platform-badge {
    background: var(--brand-bg); color: var(--brand);
    padding: 3px 9px; border-radius: 20px;
    font-size: 0.69rem; white-space: nowrap; font-weight: 600;
}

/* ════ BATTLECARD ════ */
.battlecard {
    border: 1px solid var(--border);
    border-radius: var(--r-md); overflow: hidden;
    margin-bottom: 28px; box-shadow: var(--s2);
}
.battlecard-header {
    background: linear-gradient(135deg, #08142E 0%, #0A2F72 100%);
    color: white; padding: 14px 26px;
    font-size: 1.02rem; font-weight: 600;
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.battlecard-body { display: grid; grid-template-columns: 1fr 1fr; }
.battlecard-col { padding: 20px 24px; }
.battlecard-col:first-child { background: #FFF8F8; border-right: 1px solid var(--border-2); }
.battlecard-col:last-child  { background: #F5FFF9; }
.battlecard-col h3 {
    font-size: 0.71rem; text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 12px; color: var(--ink-3); font-weight: 600;
}
.battlecard-col ul { list-style: none; }
.battlecard-col li {
    padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,0.04);
    font-size: 0.83rem; display: flex; gap: 8px; line-height: 1.5;
}
.battlecard-col li::before { content: '✓'; color: var(--green); font-weight: 700; flex-shrink: 0; }
.battlecard-col li.weakness::before { content: '✗'; color: var(--red); }
.scenarios {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    padding: 14px 24px; background: #F9FAFB; border-top: 1px solid var(--border-2);
}
.scenario-win  { background: var(--green-bg); border-radius: var(--r-sm); padding: 12px 14px; border-left: 4px solid var(--green); }
.scenario-lose { background: var(--red-bg);   border-radius: var(--r-sm); padding: 12px 14px; border-left: 4px solid var(--red); }
.scenario-title { font-size: 0.71rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.win-title  { color: var(--green); }
.lose-title { color: var(--red); }
.talking-points { padding: 14px 24px; background: white; border-top: 1px solid var(--border-2); }
.talking-points h3 { font-size: 0.71rem; color: var(--ink-3); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; }
.talking-points p {
    font-size: 0.84rem; font-style: italic; color: var(--ink-2);
    background: #F8FBFF; padding: 10px 14px; border-radius: var(--r-xs);
    line-height: 1.75; border-left: 3px solid var(--brand-mid);
}

/* ════ MARKDOWN CONTENT ════ */
.md-content { line-height: 1.85; color: var(--ink-2); }
.md-content h1 { font-size: 1.4rem; color: var(--ink-1); margin: 24px 0 12px; font-weight: 700; }
.md-content h2 { font-size: 1.08rem; color: var(--brand); margin: 22px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border-2); font-weight: 600; }
.md-content h3 { font-size: 0.95rem; color: var(--ink-1); margin: 14px 0 8px; font-weight: 600; }
.md-content p { margin-bottom: 10px; }
.md-content ul { margin: 8px 0 8px 20px; }
.md-content ol { margin: 8px 0 8px 20px; }
.md-content li { margin-bottom: 5px; }
.md-content strong { color: var(--ink-1); font-weight: 600; }
.md-content hr { border: none; border-top: 1px solid var(--border-2); margin: 20px 0; }
.md-content pre { background: #F4F6FA; padding: 14px; border-radius: var(--r-sm); overflow-x: auto; font-size: 0.8rem; margin: 10px 0; border: 1px solid var(--border-2); }
.md-content code { background: var(--border-2); padding: 1px 5px; border-radius: 4px; font-size: 0.84em; color: var(--brand-dark); }
table.md-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.82rem; }
table.md-table th { background: var(--ink-1); color: white; padding: 9px 12px; text-align: left; font-weight: 600; font-size: 0.78rem; }
table.md-table td { border: 1px solid var(--border-2); padding: 8px 12px; }
table.md-table tr:nth-child(even) td { background: #FAFBFD; }

/* ════ TIER BADGES ════ */
.tier1 { background: #FFE4E6; color: #9F1239; padding: 2px 9px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
.tier2 { background: #FEF3C7; color: #92400E; padding: 2px 9px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
.tier3 { background: #DBEAFE; color: #1E40AF; padding: 2px 9px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }

/* ════ FOOTER ════ */
.report-footer {
    text-align: center; padding: 22px; color: var(--ink-4);
    font-size: 0.75rem; margin-top: 20px;
    border-top: 1px solid var(--border-2); line-height: 1.8;
}

/* ════ EXPORT BAR ════ */
.export-bar {
    position: fixed; top: 14px; right: 14px;
    display: flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.96); padding: 9px 14px;
    border-radius: var(--r-md);
    box-shadow: var(--s3); z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, 'Microsoft JhengHei', Arial, sans-serif;
    backdrop-filter: blur(10px); border: 1px solid var(--border-2);
}
.export-label { font-size: 0.74rem; color: var(--ink-3); margin-right: 2px; font-weight: 500; }
.btn-exp {
    padding: 6px 13px; border-radius: var(--r-sm); cursor: pointer;
    font-size: 0.8rem; font-weight: 600; border: none; text-decoration: none;
    display: inline-flex; align-items: center; gap: 4px;
    transition: opacity 0.15s, transform 0.1s, box-shadow 0.15s;
}
.btn-exp:hover { opacity: 0.88; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.btn-pdf  { background: var(--red);   color: white; }
.btn-pptx { background: var(--green); color: white; }
.pptx-btn-wrap { position: relative; display: inline-block; }
.pptx-tooltip {
    display: none; position: absolute; top: calc(100% + 10px); right: 0;
    width: 290px; background: var(--ink-1); color: #ECF0F1;
    border-radius: var(--r-md); padding: 14px 16px; font-size: 0.78rem;
    line-height: 2; z-index: 2000; box-shadow: var(--s3); text-align: left; white-space: normal;
}
.pptx-tooltip::before {
    content: ''; position: absolute; top: -5px; right: 22px;
    width: 10px; height: 10px; background: var(--ink-1); transform: rotate(45deg);
}
.pptx-tooltip b  { color: #FDE68A; }
.pptx-tooltip hr { border-color: rgba(255,255,255,0.15); margin: 6px 0; }
.pptx-btn-wrap:hover .pptx-tooltip { display: block; }

/* ════ INDUSTRY VISUALIZATION (CSS-only charts) ════ */
.viz-card {
    background: var(--card); border-radius: var(--r-md); padding: 22px 24px;
    margin-bottom: 14px; border: 1px solid var(--border-2); box-shadow: var(--s1);
}
.viz-title {
    font-size: 0.93rem; font-weight: 600; color: var(--ink-1);
    margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border-2);
    display: flex; align-items: center; gap: 7px;
}
.viz-insight {
    display: flex; align-items: flex-start; gap: 9px;
    background: var(--brand-bg); border-left: 3px solid var(--brand);
    border-radius: 0 var(--r-xs) var(--r-xs) 0;
    padding: 9px 13px; margin-top: 16px;
    font-size: 0.79rem; color: var(--brand-dark); line-height: 1.65;
}
.viz-insight strong { font-weight: 600; }
.viz-insight-icon { font-size: 0.88rem; flex-shrink: 0; margin-top: 1px; }
.viz-col-title { font-size: 0.72rem; color: var(--ink-3); margin-bottom: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
/* market */
.market-range-label { font-size: 0.75rem; color: var(--ink-3); margin-bottom: 10px; }
.market-bar-track { position: relative; height: 26px; background: var(--border-2); border-radius: 7px; margin-bottom: 6px; overflow: visible; }
.market-bar-range { position: absolute; height: 100%; background: linear-gradient(90deg, var(--brand-dark), var(--brand-mid)); border-radius: 7px; opacity: 0.85; }
.market-marker { position: absolute; top: 0; transform: translateX(-50%); }
.mline { width: 2px; height: 26px; background: var(--ink-1); margin: 0 auto; opacity: 0.25; }
.mval  { font-size: 0.7rem; font-weight: 700; color: var(--ink-1); text-align: center; margin-top: 3px; white-space: nowrap; }
.market-scale-row { display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--ink-4); margin-bottom: 20px; }
.cagr-row  { display: flex; align-items: stretch; gap: 12px; }
.cagr-card { flex: 1; border-radius: var(--r-sm); padding: 14px 16px; border: 1px solid var(--border-2); background: var(--bg); }
.cagr-period { font-size: 0.7rem; color: var(--ink-3); margin-bottom: 4px; font-weight: 500; }
.cagr-value  { font-size: 1.75rem; font-weight: 700; color: var(--ink-1); line-height: 1.1; letter-spacing: -0.5px; }
.cagr-track  { height: 6px; background: var(--border-2); border-radius: 3px; margin: 9px 0 6px; }
.cagr-fill   { height: 100%; border-radius: 3px; }
.cagr-tag    { font-size: 0.69rem; color: var(--ink-3); font-weight: 500; }
.cagr-sep    { font-size: 1.5rem; color: var(--border); align-self: center; flex-shrink: 0; }
/* pyramid */
.pyramid { display: flex; flex-direction: column; gap: 7px; margin-bottom: 12px; }
.ptier { display: flex; align-items: center; gap: 12px; padding: 11px 16px; border-radius: var(--r-sm); flex-wrap: wrap; }
.pt-premium { background: linear-gradient(135deg, #FFF5F5, #FFEAEA); border-left: 4px solid var(--red); }
.pt-mid     { background: linear-gradient(135deg, #FFFBF0, #FFF3CD); border-left: 4px solid var(--amber); }
.pt-aff     { background: linear-gradient(135deg, #F0F6FF, #E0EDFF); border-left: 4px solid var(--brand); }
.ptier-badge  { font-size: 0.68rem; font-weight: 700; padding: 3px 9px; border-radius: 12px; white-space: nowrap; flex-shrink: 0; }
.t1 { background: var(--red);   color: white; }
.t2 { background: var(--amber); color: white; }
.t3 { background: var(--brand); color: white; }
.ptier-desc  { font-size: 0.8rem; flex: 1; color: var(--ink-2); line-height: 1.4; }
.ptier-price { font-size: 0.68rem; color: var(--ink-3); white-space: nowrap; flex-shrink: 0; font-weight: 500; }
.brand-tags  { display: flex; flex-wrap: wrap; gap: 6px; }
.brand-tag   { display: inline-block; background: var(--brand-bg); color: var(--brand); padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(0,82,204,0.15); }
/* consumer */
.consumer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.age-item  { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.age-lbl   { font-size: 0.73rem; width: 66px; flex-shrink: 0; color: var(--ink-2); font-weight: 500; }
.age-track { flex: 1; height: 12px; background: var(--border-2); border-radius: 6px; overflow: hidden; }
.age-fill  { height: 100%; border-radius: 6px; }
.age-pct   { font-size: 0.69rem; color: var(--ink-3); width: 36px; text-align: right; flex-shrink: 0; font-weight: 500; }
.pain-item { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }
.pain-rank { font-size: 0.72rem; font-weight: 700; width: 20px; flex-shrink: 0; text-align: center; }
.pain-body { flex: 1; }
.pain-name { font-size: 0.71rem; color: var(--ink-2); margin-bottom: 3px; font-weight: 500; }
.pain-track { height: 6px; background: var(--border-2); border-radius: 3px; overflow: hidden; }
.pain-fill  { height: 100%; border-radius: 3px; }
/* trends */
.trend-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.trend-card { background: var(--bg); border-radius: var(--r-sm); padding: 14px 12px; text-align: center; border: 1px solid var(--border-2); transition: box-shadow 0.2s, transform 0.2s; }
.trend-card:hover { box-shadow: var(--s2); transform: translateY(-2px); }
.trend-icon { font-size: 1.55rem; margin-bottom: 7px; }
.trend-name { font-size: 0.69rem; color: var(--ink-2); line-height: 1.4; margin-bottom: 7px; font-weight: 500; }
.trend-mo   { font-size: 0.66rem; font-weight: 700; }
/* risks */
.risk-grid  { display: grid; grid-template-columns: 3fr 2fr; gap: 24px; align-items: start; }
.risk-item  { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.risk-lbl   { font-size: 0.72rem; color: var(--ink-2); width: 106px; flex-shrink: 0; font-weight: 500; }
.risk-track { flex: 1; height: 8px; background: var(--border-2); border-radius: 4px; overflow: hidden; }
.risk-fill  { height: 100%; border-radius: 4px; }
.risk-sev   { font-size: 0.67rem; font-weight: 700; width: 16px; flex-shrink: 0; text-align: right; }
.stair      { border-radius: var(--r-sm); padding: 10px 13px; margin-bottom: 7px; }
.s1 { background: var(--green-bg); border-left: 3px solid var(--green); }
.s2 { background: var(--amber-bg); border-left: 3px solid var(--amber); }
.s3 { background: var(--red-bg);   border-left: 3px solid var(--red);   }
.s-lbl  { font-size: 0.73rem; font-weight: 600; color: var(--ink-1); }
.s-desc { font-size: 0.7rem; color: var(--ink-2); margin-top: 1px; }
.s-cost { font-size: 0.67rem; color: var(--ink-3); margin-top: 1px; }

/* ════ HIGHLIGHT UTILITIES ════ */
.hl       { background: #FFF176; color: #111827; padding: 1px 6px; border-radius: 3px;
            -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.hl-blue  { background: #BBDEFB; color: #0D47A1; padding: 1px 6px; border-radius: 3px;
            -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.hl-green { background: #C8E6C9; color: #1B5E20; padding: 1px 6px; border-radius: 3px;
            -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.hl-red   { background: #FFCDD2; color: #B71C1C; padding: 1px 6px; border-radius: 3px;
            -webkit-print-color-adjust: exact; print-color-adjust: exact; }
/* Auto-highlight: strong tags inside key insight containers */
.viz-insight strong,
.recommendation-item strong,
.insight-callout strong {
    background: #FFF9C4; padding: 0 3px; border-radius: 2px;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
}

/* ════ PRIORITY BADGES ════ */
.priority-badge {
    display: inline-block; font-size: 0.67rem; font-weight: 700;
    padding: 2px 8px; border-radius: 10px; margin-left: 8px;
    vertical-align: middle; white-space: nowrap;
}
.p1 { background: #FFE4E6; color: #9F1239; }
.p2 { background: #FEF3C7; color: #92400E; }
.p3 { background: #DBEAFE; color: #1E40AF; }

/* ════ KEY TAKEAWAY BOX ════ */
.key-takeaway {
    background: linear-gradient(135deg, #EBF2FF 0%, #F5F0FF 100%);
    border: 1px solid rgba(0,82,204,0.18);
    border-radius: var(--r-md); padding: 18px 22px; margin-bottom: 18px;
}
.key-takeaway-title {
    font-size: 0.72rem; font-weight: 700; color: var(--brand); text-transform: uppercase;
    letter-spacing: 0.8px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;
}
.key-takeaway-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.kt-item {
    background: rgba(255,255,255,0.8); border-radius: var(--r-sm);
    padding: 11px 14px; border: 1px solid rgba(0,82,204,0.10);
}
.kt-label { font-size: 0.7rem; color: var(--ink-3); margin-bottom: 3px; font-weight: 500; }
.kt-value { font-size: 0.87rem; color: var(--ink-1); font-weight: 600; line-height: 1.4; }

/* ════ PRINT ════ */
@media print {
    body { background: white; font-size: 11px; }
    .container { max-width: 100%; padding: 8px; }
    .kpi-grid { grid-template-columns: repeat(4, 1fr) !important; }
    .competitor-grid { grid-template-columns: repeat(3, 1fr) !important; }
    .section-card { box-shadow: none; border: 1px solid #ddd; page-break-inside: avoid; margin-bottom: 14px; }
    .battlecard { page-break-inside: avoid; box-shadow: none; }
    .viz-card { page-break-inside: avoid; box-shadow: none; }
    .export-bar { display: none !important; }
    .report-header, .battlecard-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .article-table th, table.md-table th { background: #111827 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .bar-fill, .age-fill, .pain-fill, .cagr-fill, .risk-fill, .market-bar-range { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .pt-premium, .pt-mid, .pt-aff { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .consumer-grid, .risk-grid { grid-template-columns: 1fr 1fr !important; }
    .trend-grid { grid-template-columns: repeat(5, 1fr) !important; }
    .kpi-card::before { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .hl, .hl-blue, .hl-green, .hl-red { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .key-takeaway { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .priority-badge { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .recommendation-item { border-left-color: var(--brand) !important; }
}

/* ════ RESPONSIVE ════ */
@media (max-width: 768px) {
    .container { padding: 16px 12px; }
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .competitor-grid { grid-template-columns: repeat(2, 1fr); }
    .key-takeaway-grid { grid-template-columns: 1fr; }
    .consumer-grid, .risk-grid { grid-template-columns: 1fr; }
    .trend-grid { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .cagr-row { flex-direction: column; }
    .battlecard-body { grid-template-columns: 1fr; }
    .scenarios { grid-template-columns: 1fr; }
    .report-header { padding: 28px 24px; }
    .report-header h1 { font-size: 1.45rem; }
    .meta-pill { font-size: 0.7rem; }
    .article-table, table.md-table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
}
@media (max-width: 480px) {
    .container { padding: 12px 10px; }
    .kpi-grid { grid-template-columns: 1fr; }
    .competitor-grid { grid-template-columns: 1fr; }
    .trend-grid { grid-template-columns: repeat(2, 1fr); }
    .report-header { padding: 20px 16px; }
    .report-header h1 { font-size: 1.25rem; }
    .kpi-card .kpi-number { font-size: 2.2rem; }
}
"""


class HtmlReportGenerator:
    """V2 HTML 報告生成器"""

    def __init__(self, campaign_dir: str):
        self.campaign_dir = Path(campaign_dir)
        self.data: Dict = {}

    # =========================================================
    #  資料載入
    # =========================================================

    def load_all_data(self) -> None:
        """從 campaign 目錄載入所有可用資料。"""
        d = self.campaign_dir

        # Project config
        cfg = d / "project_config.json"
        self.data['config'] = json.loads(cfg.read_text('utf-8')) if cfg.exists() else {}

        # Competitors
        comp_file = d / "competitors.json"
        if comp_file.exists():
            raw = json.loads(comp_file.read_text('utf-8'))
            if isinstance(raw, dict) and 'competitors' in raw:
                self.data['competitors'] = raw['competitors']
            elif isinstance(raw, list):
                self.data['competitors'] = raw
            else:
                self.data['competitors'] = []
        else:
            self.data['competitors'] = []

        # Keywords
        kw_file = d / "confirmed_keywords.json"
        self.data['keywords'] = json.loads(kw_file.read_text('utf-8')) if kw_file.exists() else {}

        # Dcard CSV：合併所有檔案，以連結欄（index 1）去重
        dcard_files = sorted(d.glob("dcard_*.csv"))
        self.data['dcard_headers'], self.data['dcard_rows'] = (
            self._merge_csv_files(dcard_files, url_col=1)
        )

        # PTT CSV：合併所有檔案，以文章連結欄（index 3）去重
        ptt_files = sorted(d.glob("ptt_*.csv"))
        self.data['ptt_headers'], self.data['ptt_rows'] = (
            self._merge_csv_files(ptt_files, url_col=3)
        )

        # Google News CSV：合併所有檔案，以 link 欄（index 2）去重
        news_files = sorted(d.glob("google_news_*.csv"))
        self.data['news_headers'], self.data['news_rows'] = (
            self._merge_csv_files(news_files, url_col=2)
        )

        # Deep analysis markdown (Stage 5)
        ana_file = d / "stage5_deep_analysis.md"
        self.data['deep_analysis_md'] = ana_file.read_text('utf-8') if ana_file.exists() else ""

        # Industry scan markdown (Stage 1)
        ind_file = d / "stage1_industry_scan.md"
        self.data['industry_scan_md'] = ind_file.read_text('utf-8') if ind_file.exists() else ""

        # 資料區間（供報告 header 顯示）
        meta_file = d / "campaign_meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text('utf-8'))
                start = meta.get("data_range_start")
                end = meta.get("data_range_end")
                if start and end:
                    self.data['data_range_str'] = f"{start}～{end}"
                elif meta.get("time_range_days"):
                    self.data['data_range_str'] = f"過去 {meta['time_range_days']} 天"
                else:
                    self.data['data_range_str'] = ""
            except Exception:
                self.data['data_range_str'] = ""
        else:
            self.data['data_range_str'] = ""

        # Google Trends 資料
        trends_file = d / "google_trends.json"
        self.data['google_trends'] = (
            json.loads(trends_file.read_text('utf-8')) if trends_file.exists() else {}
        )

        # 競品量化評分矩陣
        scorecard_file = d / "competitive_scorecard.json"
        self.data['scorecard'] = (
            json.loads(scorecard_file.read_text('utf-8')) if scorecard_file.exists() else {}
        )

        # 相關性過濾：將非領域文章分入 review 桶
        self._apply_relevance_filter()

    # =========================================================
    #  輔助：相關性過濾
    # =========================================================

    def _build_domain_keywords(self) -> List[str]:
        """從 config、keywords、競品名稱建立領域關鍵字清單。"""
        kws: List[str] = []
        cfg = self.data.get('config', {})
        for field in ['service', 'industry', 'brand']:
            kws.extend(w for w in cfg.get(field, '').split() if len(w) >= 2)

        kw_data = self.data.get('keywords', {})
        kw_dict = kw_data.get('keywords', kw_data) if isinstance(kw_data, dict) else {}
        for group in kw_dict.values():
            if isinstance(group, list):
                kws.extend(k for k in group if isinstance(k, str) and len(k) >= 2)

        for comp in self.data.get('competitors', []):
            name = comp.get('competitor_name', comp.get('name', ''))
            main = re.split(r'[（(]', name)[0].strip()
            if len(main) >= 2:
                kws.append(main)
            kws.extend(k for k in (comp.get('keywords', []) or []) if len(k) >= 2)

        return list({k for k in kws if k})

    # 通用約會兩性情境詞（確保相關文章不被過度過濾）
    _DATING_CONTEXT_TERMS = [
        '約會', '戀愛', '感情', '兩性', '脫單', '交友', '追求',
        '異性', '暗戀', '告白', '交往', '分手', '前任',
        '女友', '男友', '女朋友', '男朋友', '女網友', '男網友',
        '相親', '配對', '把妹', 'PUA', '情感', '伴侶', '情侶',
        '愛情', '吸引', '約炮', '曖昧', '關係'
    ]

    def _apply_relevance_filter(self) -> None:
        """
        將每個平台的文章依領域關鍵字分為「相關」與「待確認」兩個桶。
        相關 → 繼續存在原 *_rows；待確認 → 存入 *_review_rows。
        使用「領域關鍵字 OR 通用情境詞」雙軌判斷，避免過度過濾。
        """
        domain_kws = self._build_domain_keywords()
        broad_kws = list(set(domain_kws) | set(self._DATING_CONTEXT_TERMS))
        if not broad_kws:
            for p in ('dcard', 'ptt', 'news'):
                self.data[f'{p}_review_rows'] = []
            return

        def _relevant(headers: List[str], row: List[str]) -> bool:
            d = dict(zip(headers, row)) if len(row) >= len(headers) else {}
            title = (d.get('標題', '') or d.get('title', '') or '')
            # 只比對文章本身的內文/摘要，不含搜尋關鍵字欄（避免污染）
            body = (d.get('summary', '') or d.get('內文', '') or '')[:500]
            text = (title + ' ' + body).lower()
            return any(kw.lower() in text for kw in broad_kws)

        for platform, hdr_key, row_key in [
            ('dcard', 'dcard_headers', 'dcard_rows'),
            ('ptt',   'ptt_headers',   'ptt_rows'),
            ('news',  'news_headers',  'news_rows'),
        ]:
            headers = self.data.get(hdr_key, [])
            rows = self.data.get(row_key, [])
            rel, rev = [], []
            for r in rows:
                (rel if _relevant(headers, r) else rev).append(r)
            self.data[row_key] = rel
            self.data[f'{platform}_review_rows'] = rev

        total_filtered = sum(
            len(self.data.get(f'{p}_review_rows', [])) for p in ('dcard', 'ptt', 'news')
        )
        if total_filtered:
            try:
                print(f'  🔍 相關性過濾：移除 {total_filtered} 篇非領域文章（可在報告末頁查閱）', flush=True)
            except (ValueError, OSError):
                pass

    # =========================================================
    #  輔助：CSV 讀取 / 合併
    # =========================================================

    def _csv_to_rows(self, filepath: Path) -> Tuple[List[str], List[List[str]]]:
        """讀取單一 CSV，回傳 (headers, rows)。"""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                rows = [r for r in reader if any(cell.strip() for cell in r)]
            return headers, rows
        except Exception:
            return [], []

    def _merge_csv_files(self, files: List[Path],
                         url_col: int = 1) -> Tuple[List[str], List[List[str]]]:
        """
        合併多個 CSV 檔案並以 url_col 欄去重（相同 URL 只保留第一筆）。
        適用於同一次 campaign 跑多個關鍵字產生多個 CSV 的情境。
        """
        if not files:
            return [], []
        all_headers: List[str] = []
        all_rows: List[List[str]] = []
        seen: set = set()
        for f in files:
            headers, rows = self._csv_to_rows(f)
            if not all_headers and headers:
                all_headers = headers
            for row in rows:
                key = row[url_col] if len(row) > url_col and row[url_col] else tuple(row)
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)
        return all_headers, all_rows

    # =========================================================
    #  輔助：Markdown 解析
    # =========================================================

    def _parse_md_sections(self, md_text: str) -> Dict[str, str]:
        """將 Markdown 文字按 ## 標題切成 {section_name: content} dict。"""
        sections: Dict[str, str] = {}
        current: Optional[str] = None
        buf: List[str] = []
        for line in md_text.split('\n'):
            if line.startswith('## '):
                if current is not None:
                    sections[current] = '\n'.join(buf).strip()
                current = line[3:].strip()
                buf = []
            elif current is not None:
                buf.append(line)
        if current is not None:
            sections[current] = '\n'.join(buf).strip()
        return sections

    def _inline_md(self, text: str) -> str:
        """轉換 inline markdown（bold/italic/code）為 HTML。"""
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    def _escape_html(self, text: str) -> str:
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def _md_to_html(self, text: str) -> str:
        """將 Markdown 轉換為 HTML（支援 Gemini 常見輸出格式）。"""
        if not text:
            return '<p style="color:#999;">（尚未分析）</p>'

        lines = text.split('\n')
        html: List[str] = []
        in_ul = False
        in_ol = False
        in_table: Optional[str] = None  # None / 'head' / 'body'
        in_code = False

        def close_list():
            nonlocal in_ul, in_ol
            if in_ul:
                html.append('</ul>')
                in_ul = False
            if in_ol:
                html.append('</ol>')
                in_ol = False

        def close_table():
            nonlocal in_table
            if in_table == 'head':
                html.append('</thead><tbody></tbody>')
            elif in_table == 'body':
                html.append('</tbody>')
            if in_table:
                html.append('</table>')
            in_table = None

        for line in lines:
            # Code blocks
            if line.strip().startswith('```'):
                if in_code:
                    html.append('</code></pre>')
                    in_code = False
                else:
                    close_list()
                    close_table()
                    lang = line.strip()[3:].strip()
                    html.append(f'<pre><code class="lang-{lang}">')
                    in_code = True
                continue

            if in_code:
                html.append(self._escape_html(line))
                continue

            # Table rows (must start and contain at least one |)
            stripped = line.strip()
            if stripped.startswith('|') and stripped.endswith('|') and '|' in stripped[1:-1]:
                cells = [c.strip() for c in stripped[1:-1].split('|')]
                # Separator row
                is_sep = all(re.match(r'^:?-{1,}:?$', c) for c in cells if c.strip())
                if is_sep:
                    if in_table == 'head':
                        html.append('</thead><tbody>')
                        in_table = 'body'
                    continue

                if in_table is None:
                    close_list()
                    html.append('<table class="md-table"><thead>')
                    in_table = 'head'

                if in_table == 'head':
                    html.append('<tr>' + ''.join(
                        f'<th>{self._inline_md(c)}</th>' for c in cells
                    ) + '</tr>')
                    # If no separator follows immediately, treat as body
                else:
                    html.append('<tr>' + ''.join(
                        f'<td>{self._inline_md(c)}</td>' for c in cells
                    ) + '</tr>')
                continue
            else:
                close_table()

            # Headers
            if line.startswith('#### '):
                close_list()
                html.append(f'<h4>{self._inline_md(line[5:])}</h4>')
                continue
            if line.startswith('### '):
                close_list()
                html.append(f'<h3>{self._inline_md(line[4:])}</h3>')
                continue
            if line.startswith('## '):
                close_list()
                html.append(f'<h2>{self._inline_md(line[3:])}</h2>')
                continue
            if line.startswith('# '):
                close_list()
                html.append(f'<h1>{self._inline_md(line[2:])}</h1>')
                continue

            # Horizontal rule
            if re.match(r'^[-*_]{3,}$', stripped):
                close_list()
                html.append('<hr>')
                continue

            # Unordered list
            ul_match = re.match(r'^([-*+]) (.+)', line)
            if ul_match:
                if in_ol:
                    html.append('</ol>')
                    in_ol = False
                if not in_ul:
                    html.append('<ul>')
                    in_ul = True
                html.append(f'<li>{self._inline_md(ul_match.group(2))}</li>')
                continue

            # Ordered list
            ol_match = re.match(r'^(\d+)[.)]\s+(.+)', line)
            if ol_match:
                if in_ul:
                    html.append('</ul>')
                    in_ul = False
                if not in_ol:
                    html.append('<ol>')
                    in_ol = True
                html.append(f'<li>{self._inline_md(ol_match.group(2))}</li>')
                continue

            # Blank line
            if not stripped:
                close_list()
                html.append('')
                continue

            # Paragraph
            close_list()
            html.append(f'<p>{self._inline_md(line)}</p>')

        close_list()
        close_table()
        if in_code:
            html.append('</code></pre>')

        return '\n'.join(html)

    # =========================================================
    #  輔助：統計資料
    # =========================================================

    def _get_article_stats(self) -> Dict:
        dcard = len(self.data.get('dcard_rows', []))
        ptt = len(self.data.get('ptt_rows', []))
        news = len(self.data.get('news_rows', []))
        return {'dcard': dcard, 'ptt': ptt, 'news': news, 'total': dcard + ptt + news}

    def _get_top_articles(self, n: int = 5) -> List[Dict]:
        """回傳依互動排序的 top-n 文章（跨 Dcard + PTT），含留言數與文章連結。"""
        articles: List[Dict] = []

        headers = self.data.get('dcard_headers', [])
        for row in self.data.get('dcard_rows', []):
            d = dict(zip(headers, row)) if len(row) >= len(headers) else {}
            try:
                eng = float(str(d.get('互動指數', 0)).replace(',', '') or 0)
            except (ValueError, TypeError):
                eng = 0
            try:
                comment_count = int(str(d.get('回覆數', 0)).replace(',', '') or 0)
            except (ValueError, TypeError):
                comment_count = 0
            articles.append({
                'platform': 'Dcard',
                'title': (d.get('標題', '') or '')[:65],
                'engagement': eng,
                'comment_count': comment_count,
                'comment_str': f'{comment_count:,}則留言',
                'date': d.get('發布日期', ''),
                'board': d.get('看板', ''),
                'link': d.get('連結', '') or '',
                'push_raw': '',
            })

        headers = self.data.get('ptt_headers', [])
        for row in self.data.get('ptt_rows', []):
            d = dict(zip(headers, row)) if len(row) >= len(headers) else {}
            p = str(d.get('推文數', '0'))
            push_raw = p
            if p == '爆':
                eng = 100
                comment_str = '≥100則推文'
            elif p.startswith('X'):
                eng = -10
                comment_str = f'{p}則推文'
            else:
                try:
                    eng = int(p)
                    comment_str = f'{eng}則推文' if eng >= 0 else f'{p}則推文'
                except (ValueError, TypeError):
                    eng = 0
                    comment_str = '-'
            articles.append({
                'platform': 'PTT',
                'title': (d.get('標題', '') or '')[:65],
                'engagement': eng,
                'comment_count': eng,
                'comment_str': comment_str,
                'date': d.get('發佈日期', ''),
                'board': d.get('看板', ''),
                'link': d.get('文章連結', '') or '',
                'push_raw': push_raw,
            })

        articles.sort(key=lambda x: x['engagement'], reverse=True)
        return articles[:n]

    def _get_keyword_count(self) -> int:
        kd = self.data.get('keywords', {})
        if kd.get('total_count'):
            return int(kd['total_count'])
        kw_obj = kd.get('keywords', kd)
        if isinstance(kw_obj, dict):
            return sum(len(v) for v in kw_obj.values() if isinstance(v, list))
        return 0

    # =========================================================
    #  輔助：HTML 頁面包裝
    # =========================================================

    # ── 固定按鈕列 + Modal HTML ─────────────────────────────
    _EXPORT_BAR = """
<!-- ===== 匯出按鈕列（右上角固定） ===== -->
<div class="export-bar">
  <span class="export-label">匯出：</span>
  <button type="button" class="btn-exp btn-pdf" onclick="window.print()" aria-label="另存為 PDF">📥 另存 PDF</button>
  <!-- PPTX 按鈕：由 _generate_pptx_script() 注入 base64 後才顯示 -->
  <div class="pptx-btn-wrap" id="pptx-btn-wrap" style="display:none">
    <button type="button" class="btn-exp btn-pptx" onclick="downloadPptx()" aria-label="下載 PPTX 簡報檔">📊 下載 PPTX</button>
    <div class="pptx-tooltip">
      <b>下載後可匯入（文字完整可編輯）：</b>
      <hr>
      🎨 <b>Canva</b>：建立設計 → 匯入檔案 → 上傳 .pptx<br>
      📊 <b>Google 簡報</b>：檔案 → 匯入投影片 → 上傳<br>
      📝 <b>PowerPoint</b>：直接開啟即可編輯<br>
      <hr>
      ⚠️ 上傳 PDF 文字會變圖片；用 .pptx 才能自由修改內容
    </div>
  </div>
</div>
"""

    def _brand_customization(self) -> Tuple[str, str]:
        """從 project_config 讀取 logo_url、primary_color，回傳 (logo_html, extra_css)。"""
        cfg = self.data.get('config') or {}
        logo_url = (cfg.get('logo_url') or '').strip()
        primary = (cfg.get('primary_color') or cfg.get('brand_color') or '').strip()
        logo_html = ''
        if logo_url and logo_url.startswith(('http', 'https', 'data:', '/')):
            logo_html = f'<img src="{logo_url}" alt="Logo" class="report-header-logo" />'
        extra_css = ''
        if primary and re.match(r'^#([0-9A-Fa-f]{3}){1,2}$', primary):
            hex6 = primary if len(primary) == 7 else ('#' + ''.join(c*2 for c in primary[1:]))
            r, g, b = int(hex6[1:3], 16), int(hex6[3:5], 16), int(hex6[5:7], 16)
            r2, g2, b2 = max(0, int(r*0.7)), max(0, int(g*0.7)), max(0, int(b*0.7))
            dark = f'#{r2:02x}{g2:02x}{b2:02x}'
            extra_css = f':root {{ --brand: {hex6}; --brand-dark: {dark}; }}\n'
        return logo_html, extra_css

    def _html_page(self, title: str, body: str,
                   extra_css: str = '', extra_scripts: str = '') -> str:
        return (
            '<!DOCTYPE html>\n'
            '<html lang="zh-TW">\n'
            '<head>\n'
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'<title>{title}</title>\n'
            '<style>\n'
            + COMMON_CSS
            + extra_css
            + '\n</style>\n'
            '</head>\n'
            '<body>\n'
            + self._EXPORT_BAR
            + '<div class="container">\n'
            + body
            + '\n</div>\n'
            + extra_scripts
            + '\n</body>\n'
            '</html>'
        )

    def _generate_pptx_script(self, template_type: str = 'executive') -> str:
        """
        生成 PPTX → base64 編碼 → 回傳 <script> 區塊。
        注入後 HTML 按鈕會自動出現，點擊即可下載 .pptx，無需任何伺服器。
        template_type: 'executive' | 'battlecard'
        """
        try:
            import base64
            from pptx_report_generator import (
                generate_executive_pptx,
                generate_battlecard_pptx,
            )

            if template_type == 'battlecard':
                pptx_path = generate_battlecard_pptx(self.campaign_dir, self.data)
                filename = 'report_battlecard.pptx'
            else:
                pptx_path = generate_executive_pptx(self.campaign_dir, self.data)
                filename = 'report_executive_summary.pptx'

            if not pptx_path or not Path(pptx_path).exists():
                return ''

            b64 = base64.b64encode(Path(pptx_path).read_bytes()).decode('ascii')
            # 用 + 串接分段字串（陣列方式需逗號，易出錯）
            chunk = 80
            b64_chunks = ' +\n'.join(
                f'    "{b64[i:i+chunk]}"'
                for i in range(0, len(b64), chunk)
            )
            return f"""<script>
(function() {{
  var b64 =
{b64_chunks};

  var fname = "{filename}";
  window.downloadPptx = function() {{
    var bin = atob(b64);
    var arr = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    var blob = new Blob([arr], {{
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() {{ URL.revokeObjectURL(a.href); }}, 1000);
  }};
  var wrap = document.getElementById('pptx-btn-wrap');
  if (wrap) wrap.style.display = 'inline-block';
}})();
</script>"""
        except Exception as e:
            try:
                print(f'[警告] PPTX 嵌入失敗：{e}')
            except (ValueError, OSError):
                pass
            return ''

    def _tier_badge(self, label: str) -> str:
        if 'Tier 1' in label or '直接' in label:
            return '<span class="tier1">Tier 1 直接競品</span>'
        if 'Tier 2' in label or '相鄰' in label:
            return '<span class="tier2">Tier 2 相鄰方案</span>'
        if 'Tier 3' in label or '現狀' in label:
            return '<span class="tier3">Tier 3 現狀</span>'
        return ''

    # =========================================================
    #  輔助：產業掃描可視化
    # =========================================================

    def _render_industry_viz(self, industry_md: str) -> str:
        """
        產業掃描各段落轉換為 CSS-only 圖表可視化。
        每個段落採用不同巧思設計：
          1. 規模成長 → 市值範圍條 + CAGR 速率卡
          2. 玩家地圖 → 三層定位金字塔
          3. 消費者輪廓 → 年齡分布條 + 痛點熱度排行
          4. 趨勢機會 → 趨勢脈動卡片
          5. 風險門檻 → 風險熱度條 + 資本門檻階梯
        """
        if not industry_md:
            return ''

        # ── 解析 #### 段落 ───────────────────────────────────
        sections: Dict[str, str] = {}
        current_title: Optional[str] = None
        current_buf: List[str] = []
        for line in industry_md.split('\n'):
            if line.startswith('####'):
                if current_title is not None:
                    sections[current_title] = '\n'.join(current_buf).strip()
                current_title = line.lstrip('#').strip()
                current_buf = []
            elif current_title is not None:
                current_buf.append(line)
        if current_title is not None:
            sections[current_title] = '\n'.join(current_buf).strip()

        blocks: List[str] = []

        # ── Block 1：市場規模 + CAGR ──────────────────────────
        scale_text = next((v for k, v in sections.items() if '規模' in k or '成長' in k), '')
        if scale_text:
            sm = re.search(r'(\d+)\s*億.{0,30}?(\d+)\s*億', scale_text)
            size_low = int(sm.group(1)) if sm else 5
            size_high = int(sm.group(2)) if sm else 10
            cagr_all = list(re.finditer(r'CAGR.*?(\d+)\s*[%－-]\s*(\d+)\s*%', scale_text))
            hist_low = int(cagr_all[0].group(1)) if cagr_all else 15
            hist_high = int(cagr_all[0].group(2)) if cagr_all else 25
            fut_low = int(cagr_all[1].group(1)) if len(cagr_all) >= 2 else 10
            fut_high = int(cagr_all[1].group(2)) if len(cagr_all) >= 2 else 20
            max_size = max(size_high * 1.5, 15)
            low_pct = int(size_low / max_size * 100)
            rng_pct = int((size_high - size_low) / max_size * 100)
            hist_bar_pct = min(int(hist_high / 30 * 100), 100)
            fut_bar_pct = min(int(fut_high / 30 * 100), 100)
            blocks.append(f"""
<div class="viz-card">
  <div class="viz-title">📊 市場規模與成長速度</div>
  <div class="market-range-label">台灣市場年產值估計範圍（新台幣）</div>
  <div class="market-bar-track">
    <div class="market-bar-range" style="left:{low_pct}%;width:{rng_pct}%;"></div>
    <div class="market-marker" style="left:{low_pct}%;"><div class="mline"></div><div class="mval">{size_low}億</div></div>
    <div class="market-marker" style="left:{low_pct + rng_pct}%;"><div class="mline"></div><div class="mval">{size_high}億</div></div>
  </div>
  <div class="market-scale-row"><span>NT$0</span><span>5億</span><span>10億</span><span>15億+</span></div>
  <div class="cagr-row">
    <div class="cagr-card">
      <div class="cagr-period">歷史複合成長率 2021–2023</div>
      <div class="cagr-value">{hist_low}–{hist_high}%</div>
      <div class="cagr-track"><div class="cagr-fill" style="width:{hist_bar_pct}%;background:linear-gradient(90deg,#1A7F37,#34C759);"></div></div>
      <div class="cagr-tag">🚀 高速成長期</div>
    </div>
    <div class="cagr-sep">→</div>
    <div class="cagr-card">
      <div class="cagr-period">未來預測成長率 2024–2026</div>
      <div class="cagr-value">{fut_low}–{fut_high}%</div>
      <div class="cagr-track"><div class="cagr-fill" style="width:{fut_bar_pct}%;background:linear-gradient(90deg,#0052CC,#4A86D8);"></div></div>
      <div class="cagr-tag">📈 穩定成長期</div>
    </div>
  </div>
  <div class="viz-insight"><span class="viz-insight-icon">💡</span>即使進入成熟期，年複合成長率仍達 <strong>{fut_low}–{fut_high}%</strong>，遠高於整體線上教育市場均值（8–12%），市場仍具強勁進入動能。</div>
</div>""")

        # ── Block 2：競爭者定位金字塔 ─────────────────────────
        player_text = next((v for k, v in sections.items() if '玩家' in k or '品牌' in k), '')
        if player_text:
            pm = re.search(r'高端.*?[：:](.*?)(?=中端|平價|$)', player_text, re.DOTALL)
            mm = re.search(r'中端.*?[：:](.*?)(?=平價|高端|$)', player_text, re.DOTALL)
            am = re.search(r'平價.*?[：:](.*?)(?=高端|中端|####|$)', player_text, re.DOTALL)
            brands = re.findall(r'\d+\.\s+\*{0,2}([^*\n(（]+)', player_text)
            brands = [b.strip() for b in brands if len(b.strip()) > 1][:5]
            pm_txt = (pm.group(1).split('\n')[0] if pm else '個人化 VIP 深度諮詢').strip()[:60]
            mm_txt = (mm.group(1).split('\n')[0] if mm else '線上主題課程・實體工作坊').strip()[:60]
            am_txt = (am.group(1).split('\n')[0] if am else '免費講座・低價入門課').strip()[:60]
            brand_tags = ''.join(f'<span class="brand-tag">{b[:20]}</span>' for b in brands)
            blocks.append(f"""
<div class="viz-card">
  <div class="viz-title">🗺️ 競爭者定位地圖</div>
  <div class="pyramid">
    <div class="ptier pt-premium">
      <span class="ptier-badge t1">Premium 高端</span>
      <span class="ptier-desc">{pm_txt}</span>
      <span class="ptier-price">NT$3萬–15萬+</span>
    </div>
    <div class="ptier pt-mid">
      <span class="ptier-badge t2">Mid-range 中端</span>
      <span class="ptier-desc">{mm_txt}</span>
      <span class="ptier-price">NT$3,000–8,000</span>
    </div>
    <div class="ptier pt-aff">
      <span class="ptier-badge t3">Affordable 平價</span>
      <span class="ptier-desc">{am_txt}</span>
      <span class="ptier-price">NT$0–3,000</span>
    </div>
  </div>
  {'<div class="brand-tags">' + brand_tags + '</div>' if brand_tags else ''}
  <div class="viz-insight"><span class="viz-insight-icon">💡</span>市場高度碎片化，以個人品牌為主。<strong>中端市場（NT$3,000–8,000）為主流消費帶</strong>，競爭最激烈，差異化策略是勝出關鍵。</div>
</div>""")

        # ── Block 3：消費者輪廓 ────────────────────────────────
        consumer_text = next((v for k, v in sections.items() if '消費者' in k), '')
        if consumer_text:
            pain_matches = re.findall(
                r'\d+\.\s+\*{0,2}([^*\n：:（(]{3,30})[：:]?\*{0,2}', consumer_text
            )
            pain_points = [p.strip() for p in pain_matches if len(p.strip()) > 2][:6]
            pain_colors = ['#e74c3c', '#e67e22', '#f39c12', '#27ae60', '#2d6a9f', '#8e44ad']
            pain_widths = [92, 80, 70, 65, 55, 48]
            pain_rows = ''
            for idx, pp in enumerate(pain_points):
                c = pain_colors[idx % len(pain_colors)]
                w = pain_widths[idx]
                pain_rows += (
                    f'<div class="pain-item">'
                    f'<div class="pain-rank" style="color:{c};">#{idx+1}</div>'
                    f'<div class="pain-body">'
                    f'<div class="pain-name">{pp[:28]}</div>'
                    f'<div class="pain-track"><div class="pain-fill" style="width:{w}%;background:{c};"></div></div>'
                    f'</div></div>'
                )
            blocks.append(f"""
<div class="viz-card">
  <div class="viz-title">👥 消費者輪廓分析</div>
  <div class="consumer-grid">
    <div class="age-col">
      <div class="col-subtitle">核心客群年齡分布 <span style="color:#2d6a9f;font-weight:bold;">（25-45歲 佔 60-70%）</span></div>
      <div class="age-item"><div class="age-lbl">25–35歲</div><div class="age-track"><div class="age-fill" style="width:40%;background:linear-gradient(90deg,#C9000A,#E05A50);"></div></div><div class="age-pct">~40%</div></div>
      <div class="age-item"><div class="age-lbl">35–45歲</div><div class="age-track"><div class="age-fill" style="width:28%;background:linear-gradient(90deg,#B45309,#F0973E);"></div></div><div class="age-pct">~28%</div></div>
      <div class="age-item"><div class="age-lbl">45歲以上</div><div class="age-track"><div class="age-fill" style="width:18%;background:linear-gradient(90deg,#0052CC,#4A86D8);"></div></div><div class="age-pct">~18%</div></div>
      <div class="age-item"><div class="age-lbl">25歲以下</div><div class="age-track"><div class="age-fill" style="width:14%;background:#C0C8D8;"></div></div><div class="age-pct">~14%</div></div>
      <div class="viz-insight" style="margin-top:12px;"><span class="viz-insight-icon">💡</span>25–45歲合計 <strong>佔 68%</strong>，是核心付費決策群體。</div>
    </div>
    <div class="pain-col">
      <div class="col-subtitle">消費者痛點排行（熱度）</div>
      {pain_rows or '<p style="color:#999;font-size:0.8rem;">（請完成 Stage 1 分析後自動填入）</p>'}
    </div>
  </div>
</div>""")

        # ── Block 4：產業趨勢 ──────────────────────────────────
        trend_text = next((v for k, v in sections.items() if '趨勢' in k or '機會' in k), '')
        if trend_text:
            trends = re.findall(r'\d+\.\s+\*{0,2}([^*\n：:]{4,40})[：:]?\*{0,2}', trend_text)
            trends = [t.strip() for t in trends if len(t.strip()) > 3][:5]
            icons = ['🤖', '🧠', '💚', '🤝', '🔗']
            colors = ['#3498db', '#9b59b6', '#27ae60', '#e67e22', '#1abc9c']
            momentums = ['🔥 熱門', '⬆ 上升', '✅ 成熟', '💡 新興', '🌱 潛力']
            trend_cards = ''
            for idx, t in enumerate(trends):
                ic = icons[idx % len(icons)]
                cl = colors[idx % len(colors)]
                mo = momentums[idx % len(momentums)]
                trend_cards += (
                    f'<div class="trend-card" style="border-top:3px solid {cl};">'
                    f'<div class="trend-icon">{ic}</div>'
                    f'<div class="trend-name">{t[:30]}</div>'
                    f'<div class="trend-mo" style="color:{cl};">{mo}</div>'
                    f'</div>'
                )
            blocks.append(f"""
<div class="viz-card">
  <div class="viz-title">🔭 產業趨勢脈動</div>
  <div class="trend-grid">{trend_cards}</div>
  <div class="viz-insight"><span class="viz-insight-icon">💡</span>AI 個人化與「非 PUA 真誠關係建立」並列最強趨勢。市場正從技巧導向轉型為<strong>心理與真誠導向</strong>，掌握此趨勢的品牌具備顯著差異化優勢。</div>
</div>""")

        # ── Block 5：風險 + 資本門檻 ──────────────────────────
        risk_text = next((v for k, v in sections.items() if '門檻' in k or '風險' in k), '')
        if risk_text:
            risks = re.findall(r'\d+\.\s+\*{0,2}([^*\n：:]{4,30})[：:]?\*{0,2}', risk_text)
            risks = [r.strip() for r in risks if len(r.strip()) > 3][:6]
            r_sev = ['高', '高', '中', '高', '中', '低']
            r_col = {'高': '#e74c3c', '中': '#e67e22', '低': '#27ae60'}
            r_wid = {'高': 80, '中': 55, '低': 30}
            risk_rows = ''
            for idx, r in enumerate(risks):
                sev = r_sev[idx] if idx < len(r_sev) else '中'
                c = r_col.get(sev, '#e67e22')
                w = r_wid.get(sev, 55)
                risk_rows += (
                    f'<div class="risk-item">'
                    f'<div class="risk-lbl">{r[:24]}</div>'
                    f'<div class="risk-track"><div class="risk-fill" style="width:{w}%;background:{c};"></div></div>'
                    f'<div class="risk-sev" style="color:{c};">{sev}</div>'
                    f'</div>'
                )
            blocks.append(f"""
<div class="viz-card">
  <div class="viz-title">⚠️ 風險地圖 ＆ 資本門檻</div>
  <div class="risk-grid">
    <div>
      <div class="col-subtitle">主要風險熱度</div>
      {risk_rows or '<p style="color:#999;font-size:0.8rem;">（尚無資料）</p>'}
    </div>
    <div>
      <div class="col-subtitle">進入門檻梯度</div>
      <div class="stair s1"><div class="s-lbl">低門檻入場</div><div class="s-desc">個人教練・內容創作者</div><div class="s-cost">主要為時間與知識成本</div></div>
      <div class="stair s2"><div class="s-lbl">中門檻建立品牌</div><div class="s-desc">品牌建立・小型工作室</div><div class="s-cost">設備＋平台＋行銷費用</div></div>
      <div class="stair s3"><div class="s-lbl">高門檻規模化</div><div class="s-desc">科技平台・大型服務商</div><div class="s-cost">AI研發＋大規模行銷</div></div>
      <div class="viz-insight"><span class="viz-insight-icon">💡</span><strong>聲譽風險</strong>是最高危項目——服務效果難量化，負評在社群擴散的影響遠超廣告效益。</div>
    </div>
  </div>
</div>""")

        if not blocks:
            return ''

        return f'<div class="viz-wrapper">{"".join(blocks)}</div>'

    def _get_competitor_ta_map(self) -> Dict[str, str]:
        """Parse 競品維度彙總 table to get TA (target audience) info per competitor."""
        sections = self._parse_md_sections(self.data.get('deep_analysis_md', ''))
        dim_md = next((v for k, v in sections.items() if '競品維度彙總' in k), '')
        ta_map: Dict[str, str] = {}
        if not dim_md:
            return ta_map
        lines = dim_md.split('\n')
        header_cols: List[str] = []
        ta_col = -1
        for ln in lines:
            if not ln.strip().startswith('|'):
                continue
            cells = [c.strip() for c in ln.strip('|').split('|')]
            if all(re.match(r'^[:\- ]+$', c) for c in cells if c.strip()):
                continue
            if not header_cols:
                header_cols = cells
                for j, h in enumerate(header_cols):
                    if '目標受眾' in h or ('TA' in h and '輪廓' in h):
                        ta_col = j
                continue
            if ta_col >= 0 and len(cells) > ta_col:
                name = re.sub(r'\*+', '', cells[0]).strip()
                ta = cells[ta_col].strip()
                if name:
                    ta_map[name] = ta
        return ta_map

    # =========================================================
    #  新增：數據驅動視覺化
    # =========================================================

    def _compute_monthly_nss(self) -> dict:
        """
        從現有 Dcard / PTT CSV 資料按月計算淨情緒分數（NSS）。

        Returns:
            {'Dcard': [{'month':'2024-01','nss':23.5,'pos':12,'neg':5,'total':40}, ...],
             'PTT':   [...]}
        """
        try:
            from sentiment_config import get_positive_words, get_negative_words
            pos_words = get_positive_words()
            neg_words = get_negative_words()
        except ImportError:
            pos_words = ["推薦", "好用", "讚", "滿意", "有效"]
            neg_words = ["雷", "爛", "騙", "失望", "後悔"]

        cfg = self.data.get('config', {})
        industry = cfg.get('industry')

        try:
            from sentiment_config import get_negative_words as _gnw
            neg_words = _gnw(industry)
        except Exception:
            pass

        result = {}
        platform_map = [
            ('Dcard', 'dcard_headers', 'dcard_rows', '發布日期', '內文', '標題'),
            ('PTT',   'ptt_headers',   'ptt_rows',   '發佈日期', '內文', '標題'),
        ]

        for platform, hdr_key, rows_key, date_col, content_col, title_col in platform_map:
            headers = self.data.get(hdr_key, [])
            rows    = self.data.get(rows_key, [])
            if not headers or not rows:
                continue

            # 找到欄位 index
            try:
                date_idx    = headers.index(date_col)
            except ValueError:
                date_idx    = 3  # fallback
            try:
                content_idx = headers.index(content_col)
            except ValueError:
                content_idx = 6
            try:
                title_idx   = headers.index(title_col)
            except ValueError:
                title_idx   = 0

            # 按月分組計算 NSS
            monthly: dict = {}
            for row in rows:
                if len(row) <= max(date_idx, content_idx, title_idx):
                    continue
                raw_date = str(row[date_idx] or '')
                month = raw_date[:7]  # 取 "YYYY-MM"
                if not month or len(month) < 7:
                    continue
                text = (str(row[title_idx] or '') + ' ' + str(row[content_idx] or ''))
                is_pos = any(w in text for w in pos_words)
                is_neg = any(w in text for w in neg_words)
                if month not in monthly:
                    monthly[month] = {'pos': 0, 'neg': 0, 'total': 0}
                monthly[month]['total'] += 1
                if is_pos:
                    monthly[month]['pos'] += 1
                if is_neg:
                    monthly[month]['neg'] += 1

            # 轉換為有序列表
            series = []
            for month in sorted(monthly.keys())[-12:]:  # 最近 12 個月
                d = monthly[month]
                nss = round((d['pos'] - d['neg']) / d['total'] * 100, 1) if d['total'] else 0.0
                series.append({
                    'month': month, 'nss': nss,
                    'pos': d['pos'], 'neg': d['neg'], 'total': d['total'],
                })
            if series:
                result[platform] = series

        return result

    def _render_sentiment_timeline(self) -> str:
        """
        生成月度情緒趨勢 SVG 折線圖（純 SVG，無外部依賴）。
        Y 軸：NSS -100 ~ +100；X 軸：月份；0 基準線為虛線。
        """
        monthly_data = self._compute_monthly_nss()
        if not monthly_data:
            return ''

        # 收集所有月份並排序
        all_months = sorted({pt['month'] for series in monthly_data.values() for pt in series})
        if len(all_months) < 2:
            return ''

        W, H = 620, 220
        PAD_L, PAD_R, PAD_T, PAD_B = 48, 20, 20, 52
        chart_w = W - PAD_L - PAD_R
        chart_h = H - PAD_T - PAD_B
        NSS_MIN, NSS_MAX = -100, 100

        def x_pos(i: int) -> float:
            return PAD_L + i / (len(all_months) - 1) * chart_w

        def y_pos(nss: float) -> float:
            return PAD_T + (1 - (nss - NSS_MIN) / (NSS_MAX - NSS_MIN)) * chart_h

        zero_y = y_pos(0)

        # SVG 顏色
        colors = {'Dcard': '#4A6CF7', 'PTT': '#e74c3c'}
        bg_colors = {'Dcard': 'rgba(74,108,247,0.08)', 'PTT': 'rgba(231,76,60,0.08)'}

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'style="width:100%;max-width:{W}px;display:block;margin:0 auto;font-family:inherit;">',
        ]

        # 背景格線（-50、0、+50）
        for nss_val in [-50, 0, 50]:
            yv = y_pos(nss_val)
            dash = '4,4' if nss_val != 0 else '6,3'
            stroke = '#aaa' if nss_val == 0 else '#ddd'
            sw = '1.5' if nss_val == 0 else '1'
            parts.append(
                f'<line x1="{PAD_L}" y1="{yv:.1f}" x2="{W - PAD_R}" y2="{yv:.1f}" '
                f'stroke="{stroke}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
            )
            label = f'+{nss_val}' if nss_val > 0 else str(nss_val)
            parts.append(
                f'<text x="{PAD_L - 4}" y="{yv + 4:.1f}" text-anchor="end" '
                f'font-size="9" fill="#888">{label}</text>'
            )

        # 折線：先畫填充 area，再畫線
        for platform, series in monthly_data.items():
            color = colors.get(platform, '#888')
            bg    = bg_colors.get(platform, 'rgba(136,136,136,0.08)')
            idx_map = {pt['month']: i for i, pt in enumerate(
                [{'month': m} for m in all_months]
            )}
            pts = []
            for pt in series:
                xi = all_months.index(pt['month'])
                pts.append((x_pos(xi), y_pos(pt['nss'])))

            if len(pts) < 2:
                continue

            # 填充 area（正區間用品牌色，負區間用紅色）
            area_pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
            area_pts += f' {pts[-1][0]:.1f},{zero_y:.1f} {pts[0][0]:.1f},{zero_y:.1f}'
            parts.append(
                f'<polygon points="{area_pts}" fill="{bg}" stroke="none"/>'
            )

            # 折線
            line_pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
            parts.append(
                f'<polyline points="{line_pts}" fill="none" stroke="{color}" '
                f'stroke-width="2" stroke-linejoin="round"/>'
            )

            # 資料點
            for (x, y), pt in zip(pts, series):
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" '
                    f'stroke="white" stroke-width="1"/>'
                )

        # X 軸月份標籤（每 2 個月顯示一次）
        for i, month in enumerate(all_months):
            if i % 2 == 0 or i == len(all_months) - 1:
                xv = x_pos(i)
                label = month[2:]  # "24-01" 格式
                parts.append(
                    f'<text x="{xv:.1f}" y="{H - PAD_B + 14}" text-anchor="middle" '
                    f'font-size="9" fill="#888" transform="rotate(-30,{xv:.1f},{H - PAD_B + 14})">'
                    f'{label}</text>'
                )

        # 圖例
        legend_x = PAD_L
        for i, (platform, color) in enumerate(colors.items()):
            if platform in monthly_data:
                lx = legend_x + i * 90
                ly = H - 8
                parts.append(
                    f'<line x1="{lx}" y1="{ly}" x2="{lx + 18}" y2="{ly}" '
                    f'stroke="{color}" stroke-width="2"/>'
                )
                parts.append(
                    f'<text x="{lx + 22}" y="{ly + 4}" font-size="10" fill="#555">{platform}</text>'
                )

        parts.append('</svg>')

        svg_html = '\n'.join(parts)
        return f'''<div class="section-card">
  <h2>📈 月度情緒趨勢（淨情緒分數 NSS）</h2>
  <p style="font-size:0.8rem;color:#777;margin-bottom:12px;">
    NSS = (正面文章數 - 負面文章數) / 總文章數 × 100。
    &gt;0 表示正面情緒佔優，&lt;0 表示負面情緒佔優。
    資料來源：Dcard / PTT 現有爬蟲結果。
  </p>
  {svg_html}
</div>'''

    def _render_scorecard_section(self, compact: bool = False) -> str:
        """
        生成競品量化評分矩陣：SVG 雷達圖 + 維度分數明細表。

        Args:
            compact — True 時僅顯示明細表（供 Battlecard 使用），False 時顯示雷達圖
        """
        scorecard = self.data.get('scorecard', {})
        if not scorecard or not scorecard.get('scores'):
            return ''

        dimensions = scorecard.get('dimensions', [])
        scores     = scorecard.get('scores', {})
        brand      = scorecard.get('brand', '')
        data_src   = scorecard.get('data_sources', {})
        all_names  = [brand] + [c for c in scores if c != brand]

        if not dimensions or not all_names:
            return ''

        # ── 雷達圖 SVG ──────────────────────────────────────────
        import math
        CX, CY, R = 160, 160, 110
        N = len(dimensions)
        MAX_VAL = 5.0

        # 品牌用主色，競品用灰色系
        plot_colors = {brand: ('#4A6CF7', 'rgba(74,108,247,0.18)')}
        gray_palette = [
            ('#e74c3c', 'rgba(231,76,60,0.12)'),
            ('#27ae60', 'rgba(39,174,96,0.12)'),
            ('#f39c12', 'rgba(243,156,18,0.12)'),
            ('#8e44ad', 'rgba(142,68,173,0.12)'),
        ]
        for i, name in enumerate([n for n in all_names if n != brand]):
            plot_colors[name] = gray_palette[i % len(gray_palette)]

        def axis_angle(i: int) -> float:
            return math.radians(90 - 360 * i / N)

        def pt(i: int, val: float) -> tuple:
            r = R * max(0, val) / MAX_VAL
            a = axis_angle(i)
            return CX + r * math.cos(a), CY - r * math.sin(a)

        svg_w, svg_h = 320, 320
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
            f'style="width:100%;max-width:{svg_w}px;display:block;font-family:inherit;">',
        ]

        # 背景網格（1–5 各一圈）
        for level in range(1, 6):
            grid_pts = ' '.join(
                f'{CX + R * level / MAX_VAL * math.cos(axis_angle(i)):.1f},'
                f'{CY - R * level / MAX_VAL * math.sin(axis_angle(i)):.1f}'
                for i in range(N)
            )
            svg_parts.append(
                f'<polygon points="{grid_pts}" fill="none" stroke="#e0e0e0" stroke-width="1"/>'
            )

        # 軸線
        for i in range(N):
            ex, ey = CX + R * math.cos(axis_angle(i)), CY - R * math.sin(axis_angle(i))
            svg_parts.append(
                f'<line x1="{CX}" y1="{CY}" x2="{ex:.1f}" y2="{ey:.1f}" '
                f'stroke="#ccc" stroke-width="1"/>'
            )

        # 軸標籤
        for i, dim in enumerate(dimensions):
            lx = CX + (R + 22) * math.cos(axis_angle(i))
            ly = CY - (R + 22) * math.sin(axis_angle(i))
            anchor = 'middle'
            if lx < CX - 5:
                anchor = 'end'
            elif lx > CX + 5:
                anchor = 'start'
            short = dim[:5]  # 最多 5 個字
            svg_parts.append(
                f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}" '
                f'font-size="9" fill="#555">{short}</text>'
            )

        # 每個品牌/競品的 polygon（最多顯示 5 個）
        for name in all_names[:5]:
            name_scores = scores.get(name, {})
            color, fill = plot_colors.get(name, ('#888', 'rgba(136,136,136,0.1)'))
            data_pts = ' '.join(
                f'{pt(i, name_scores.get(dim, 0) if name_scores.get(dim, -1) >= 0 else 0)[0]:.1f},'
                f'{pt(i, name_scores.get(dim, 0) if name_scores.get(dim, -1) >= 0 else 0)[1]:.1f}'
                for i, dim in enumerate(dimensions)
            )
            sw = '2' if name == brand else '1.5'
            svg_parts.append(
                f'<polygon points="{data_pts}" fill="{fill}" stroke="{color}" stroke-width="{sw}"/>'
            )

        # 圖例
        legend_y = svg_h - 10
        for i, name in enumerate(all_names[:5]):
            color, _ = plot_colors.get(name, ('#888', ''))
            lx = 10 + i * 60
            label = ('★ ' + name) if name == brand else name
            svg_parts.append(
                f'<circle cx="{lx + 5}" cy="{legend_y - 3}" r="4" fill="{color}"/>'
                f'<text x="{lx + 12}" y="{legend_y}" font-size="9" fill="#444">{label[:6]}</text>'
            )

        svg_parts.append('</svg>')
        radar_svg = '\n'.join(svg_parts)

        # ── 維度分數明細表 ──────────────────────────────────────
        th_cells = '<th>維度</th>' + ''.join(
            f'<th>{"★ " if n == brand else ""}{n[:8]}</th>' for n in all_names[:5]
        )
        table_rows = ''
        for dim in dimensions:
            src_note = data_src.get(dim, '')
            row = f'<td title="{src_note}" style="cursor:help;">{dim}</td>'
            for name in all_names[:5]:
                val = scores.get(name, {}).get(dim, -1.0)
                if val < 0:
                    cell = '<td style="color:#aaa;text-align:center;">N/A</td>'
                else:
                    bar_w = int(val / MAX_VAL * 100)
                    color, _ = plot_colors.get(name, ('#888', ''))
                    cell = (
                        f'<td style="text-align:center;">'
                        f'<div style="background:#f0f0f0;border-radius:4px;height:6px;margin-bottom:2px;">'
                        f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:4px;"></div></div>'
                        f'<span style="font-size:0.75rem;font-weight:bold;">{val:.1f}</span></td>'
                    )
                row += cell
            table_rows += f'<tr>{row}</tr>'

        table_html = (
            f'<table class="article-table" style="font-size:0.82rem;">'
            f'<thead><tr>{th_cells}</tr></thead>'
            f'<tbody>{table_rows}</tbody></table>'
            f'<p style="font-size:0.72rem;color:#999;margin-top:8px;">'
            f'* 滑鼠移到「維度」名稱可查看資料來源。N/A = 本輪無對應資料。</p>'
        )

        if compact:
            return f'<div class="section-card"><h3>📊 量化評分矩陣（0–5 分）</h3>{table_html}</div>'

        return f'''<div class="section-card">
  <h2>📊 競品量化評分矩陣（0–5 分）</h2>
  <p style="font-size:0.8rem;color:#777;margin-bottom:16px;">
    6 個維度綜合評分，資料來源：Google Trends、社群 CSV、媒體曝光、AI 分析。
    N/A 表示本輪缺乏對應資料。
  </p>
  <div style="display:flex;gap:28px;align-items:flex-start;flex-wrap:wrap;">
    <div style="flex:0 0 auto;">{radar_svg}</div>
    <div style="flex:1;min-width:280px;">{table_html}</div>
  </div>
</div>'''

    def _render_google_trends_section(self) -> str:
        """
        生成 Google Trends Share of Search 橫條圖（複用現有 .bar-chart CSS）。
        """
        trends = self.data.get('google_trends', {})
        sos = trends.get('share_of_search', {})
        r3m = trends.get('recent_3m_avg', {})
        brand = self.data.get('config', {}).get('brand', '')

        if not sos:
            return ''

        # 依 SoS 排序（高到低）
        sorted_sos = sorted(sos.items(), key=lambda x: x[1], reverse=True)
        max_sos = sorted_sos[0][1] if sorted_sos else 1

        bar_items = ''
        for name, share in sorted_sos:
            pct_bar = int(share / max_sos * 100) if max_sos else 0
            is_brand = (name == brand)
            color = '#4A6CF7' if is_brand else '#aab5d0'
            label_extra = ' ★ 自有品牌' if is_brand else ''
            avg_3m = r3m.get(name, 0)
            bar_items += f'''<li class="bar-item">
  <span class="bar-label" style="{"font-weight:bold;" if is_brand else ""}">{name}{label_extra}</span>
  <div class="bar-track">
    <div class="bar-fill" style="width:{pct_bar}%;background:{color};"></div>
  </div>
  <span class="bar-value">{share:.1f}% <small style="color:#aaa;">（近 3 月均指數 {avg_3m:.0f}）</small></span>
</li>'''

        scraped_at = trends.get('scraped_at', '')[:10]
        note = f'資料抓取日期：{scraped_at}，' if scraped_at else ''

        return f'''<div class="section-card">
  <h2>🔍 Google 搜尋聲量 Share of Search</h2>
  <p style="font-size:0.8rem;color:#777;margin-bottom:12px;">
    {note}台灣地區 Google 搜尋趨勢（過去 12 個月），數值為各品牌搜尋量佔比。
    搜尋量代表品牌「主動被尋找」的程度，是最客觀的市場知名度指標之一。
  </p>
  <ul class="bar-chart">{bar_items}</ul>
</div>'''

    # =========================================================
    #  Template 1：執行摘要版
    # =========================================================

    def generate_executive_summary(self) -> str:
        cfg = self.data.get('config', {})
        brand = cfg.get('brand', '品牌')
        service = cfg.get('service', '產品')
        industry = cfg.get('industry', '產業')
        purpose = cfg.get('purpose', '競品分析')
        audience = cfg.get('audience', '目標受眾')

        competitors = self.data.get('competitors', [])
        stats = self._get_article_stats()
        keyword_count = self._get_keyword_count()
        platform_count = sum(1 for v in [stats['dcard'], stats['ptt'], stats['news']] if v > 0)
        top_articles = self._get_top_articles(5)
        filtered_count = sum(
            len(self.data.get(f'{p}_review_rows', []))
            for p in ('dcard', 'ptt', 'news')
        )

        # KPI Cards
        filter_card = (
            f'<div class="kpi-card" style="border-top:3px solid #e67e22;">'
            f'<div class="kpi-number" style="color:#e67e22;">{filtered_count}</div>'
            f'<div class="kpi-label">過濾非相關文章</div></div>'
        ) if filtered_count else ''
        kpi_html = f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-number">{len(competitors)}</div><div class="kpi-label">競品數量</div></div>
  <div class="kpi-card"><div class="kpi-number">{stats['total']:,}</div><div class="kpi-label">有效分析文章</div></div>
  <div class="kpi-card"><div class="kpi-number">{keyword_count}</div><div class="kpi-label">追蹤關鍵字</div></div>
  <div class="kpi-card"><div class="kpi-number">{platform_count}</div><div class="kpi-label">監測平台</div></div>
  {filter_card}
</div>"""

        # Competitor Cards (all competitors)
        comp_cards = ''
        for i, comp in enumerate(competitors, 1):
            name = comp.get('competitor_name', comp.get('name', f'競品{i}'))
            label = comp.get('label', comp.get('tags', ''))
            fan = (comp.get('fan_profile', '') or '')[:50]
            kws = ', '.join((comp.get('keywords', []) or [])[:3])
            badge = self._tier_badge(label)
            comp_cards += f"""<div class="competitor-card">
  <div class="comp-name">{name}</div>
  {'<span class="comp-label">' + label[:30] + '</span>' if label else ''}
  {badge}
  {'<div class="comp-fan">' + fan + '</div>' if fan else ''}
  {'<div class="comp-kws">' + kws + '</div>' if kws else ''}
</div>"""

        comp_section = (
            f'<div class="section-card"><h2>🎯 主要競品（{len(competitors)} 個）</h2>'
            f'<div class="competitor-grid">{comp_cards}</div></div>'
        ) if competitors else ''

        # Platform bar chart
        platform_stats_list = [
            ('Dcard', stats['dcard']),
            ('PTT', stats['ptt']),
            ('Google 新聞', stats['news']),
        ]
        max_val = max((c for _, c in platform_stats_list), default=1) or 1
        bar_html = '<ul class="bar-chart">'
        for label, count in platform_stats_list:
            pct = int(count / max_val * 100)
            bar_html += (
                f'<li class="bar-item">'
                f'<span class="bar-label">{label}</span>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
                f'<span class="bar-value">{count:,} 篇</span>'
                f'</li>'
            )
        bar_html += '</ul>'

        # Top articles table
        art_rows = ''
        for a in top_articles:
            link = a.get('link', '')
            _tit = (a["title"] or "")[:80]
            title_cell = (
                f'<a href="{link}" target="_blank" rel="noopener noreferrer" class="article-link" aria-label="閱讀文章：{_tit}">{a["title"]}</a>'
                if link else a['title']
            )
            art_rows += (
                f'<tr>'
                f'<td><span class="platform-badge">{a["platform"]}</span></td>'
                f'<td>{title_cell}</td>'
                f'<td>{a["board"]}</td>'
                f'<td class="engagement" style="white-space:nowrap;">{a.get("comment_str", "-")}</td>'
                f'<td style="white-space:nowrap;font-size:0.78rem;">{a["date"]}</td>'
                f'</tr>'
            )
        articles_section = (
            '<div class="section-card"><h2>📰 高互動社群文章 TOP 5</h2>'
            '<table class="article-table">'
            '<thead><tr><th>平台</th><th>標題（可點擊）</th><th>看板</th><th>留言數</th><th>日期</th></tr></thead>'
            f'<tbody>{art_rows}</tbody></table></div>'
        ) if art_rows else ''

        # Strategy recommendations from AI analysis
        sections = self._parse_md_sections(self.data.get('deep_analysis_md', ''))
        strategy_md = next(
            (v for k, v in sections.items() if '行銷策略' in k or '行銷建議' in k),
            ''
        )
        recs: List[str] = []
        if strategy_md:
            for m in re.finditer(r'(?:^|\n)\d+[.、]\s*\*{0,2}(.+?)\*{0,2}(?:\n|$)', strategy_md):
                txt = m.group(1).strip()
                if txt and len(txt) > 5:
                    recs.append(txt[:300])
            # Also grab any ### sub-headers as recommendations
            if not recs:
                for m in re.finditer(r'###\s+(.+)', strategy_md):
                    recs.append(m.group(1).strip()[:200])

        if not recs:
            recs = ['（請先完成 Stage 5 深度分析，此處將自動填入 AI 策略建議）']

        priority_labels = ['P1 立即執行', 'P2 本月內', 'P2 本月內', 'P3 下季度', 'P3 下季度']
        priority_cls    = ['p1', 'p2', 'p2', 'p3', 'p3']
        rec_html = ''
        for i, rec in enumerate(recs[:5], 1):
            p_cls   = priority_cls[i - 1]
            p_label = priority_labels[i - 1]
            rec_html += (
                f'<div class="recommendation-item">'
                f'<div class="rec-number">{i}</div>'
                f'<div class="rec-content">'
                f'<span class="priority-badge {p_cls}">{p_label}</span> {rec}'
                f'</div>'
                f'</div>'
            )

        # Key Takeaway box: top insight snapshot
        kt_total = stats['total']
        kt_comps = len(competitors)
        kt_kws   = keyword_count
        top_platform = max(platform_stats_list, key=lambda x: x[1], default=('—', 0))[0]
        key_takeaway_html = f"""<div class="key-takeaway">
  <div class="key-takeaway-title">⚡ 本次分析快照</div>
  <div class="key-takeaway-grid">
    <div class="kt-item"><div class="kt-label">有效分析文章</div><div class="kt-value">{kt_total:,} 篇</div></div>
    <div class="kt-item"><div class="kt-label">競品數量</div><div class="kt-value">{kt_comps} 個競品</div></div>
    <div class="kt-item"><div class="kt-label">聲量最高平台</div><div class="kt-value">{top_platform}</div></div>
  </div>
</div>"""

        logo_frag, brand_css = self._brand_customization()
        now_str = datetime.now().strftime('%Y年%m月%d日')
        data_range = self.data.get('data_range_str') or ''
        data_pill = f'<span class="meta-pill">📊 資料區間：{data_range}</span>' if data_range else ''
        body = f"""
<div class="report-header">
  {logo_frag}
  <h1>競品分析報告：{brand}</h1>
  <div class="subtitle">{purpose} ｜ {industry} 產業 ｜ 核心產品／服務：{service}</div>
  <div class="meta"><span class="meta-pill">📅 {now_str}</span><span class="meta-pill">👤 {audience}</span>{data_pill}<span class="meta-pill">執行摘要版</span></div>
</div>

{kpi_html}

{key_takeaway_html}

{comp_section}

<div class="section-card">
  <h2>📊 社群聲量分布</h2>
  {bar_html}
</div>

{articles_section}

<div class="section-card">
  <h2>💡 行銷策略建議</h2>
  {rec_html}
</div>

<div class="section-card">
  <h2>📌 建議下一步行動</h2>
  <ol style="padding-left:22px;line-height:2.1;font-size:0.88rem;">
    <li><strong>本週</strong>：詳讀競品 Battlecard，確認競爭優勢與反制話術</li>
    <li><strong>2 週內</strong>：根據社群痛點制定內容行銷計劃，啟動素材製作</li>
    <li><strong>1 個月內</strong>：上線第一波測試廣告，監控 Dcard／PTT 社群反應</li>
  </ol>
</div>

<div class="report-footer">
  報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 系統版本：V2.0 ｜ 執行摘要版<br>
  📌 按右上角「<strong>📊 下載 PPTX</strong>」可下載簡報檔，匯入 Canva / Google 簡報 / PowerPoint 即可編輯<br>
  <span style="margin-top:10px;display:inline-block;font-size:0.7rem;color:var(--ink-4);">
    <strong>方法論</strong>：資料來源為 Dcard、PTT、Google 新聞等公開管道；取樣依關鍵字與設定之時間範圍搜尋，部分渠道依互動數排序取前 N 篇。<br>
    <strong>免責聲明</strong>：本報告供內部策略參考，數據來自公開來源與自動化擷取，請依需要驗證關鍵資訊後再行決策。
  </span>
</div>
"""

        # 新：Google Trends + 競品評分矩陣
        trends_section   = self._render_google_trends_section()
        scorecard_section = self._render_scorecard_section()

        body = body.replace(
            '<div class="section-card">\n  <h2>📊 社群聲量分布</h2>',
            f'{trends_section}\n\n<div class="section-card">\n  <h2>📊 社群聲量分布</h2>',
        )
        if scorecard_section:
            body = body + '\n\n' + scorecard_section

        pptx_script = self._generate_pptx_script('executive')
        html = self._html_page(f'執行摘要 - {brand} 競品分析', body,
                               extra_css=brand_css, extra_scripts=pptx_script)
        out = self.campaign_dir / 'report_executive_summary.html'
        out.write_text(html, encoding='utf-8')
        try: print(f'  ✅ 執行摘要版：{out.name}')
        except (ValueError, OSError): pass
        return str(out)

    # =========================================================
    #  Template 2：競品對決版（Battlecard）
    # =========================================================

    def generate_battlecard(self) -> str:
        cfg = self.data.get('config', {})
        brand = cfg.get('brand', '我方品牌')
        service = cfg.get('service', '產品')

        competitors = self.data.get('competitors', [])

        # Extract battlecard section from AI analysis
        sections = self._parse_md_sections(self.data.get('deep_analysis_md', ''))
        battlecard_md = next(
            (v for k, v in sections.items() if 'Battlecard' in k),
            ''
        )

        def _extract_list_items(text: str) -> List[str]:
            items = []
            for line in text.split('\n'):
                m = re.match(r'^\s*[-*•]\s+(.+)', line)
                if m:
                    items.append(m.group(1).strip()[:150])
                elif re.match(r'^\s*\d+[.)]\s+(.+)', line):
                    items.append(re.sub(r'^\s*\d+[.)]\s+', '', line).strip()[:150])
            return items

        def _extract_subsection(text: str, *keys: str) -> str:
            for key in keys:
                m = re.search(
                    rf'(?:^|\n)\*{{0,2}}{re.escape(key)}\*{{0,2}}[：:]\s*(.*?)(?=\n\*{{0,2}}[^*\n]{{2,}}\*{{0,2}}[：:]|\Z)',
                    text, re.DOTALL
                )
                if m:
                    return m.group(1).strip()[:400]
            return ''

        def _table_cell(text: str, *header_kws: str) -> str:
            """Find content in a Markdown table column whose header contains any keyword."""
            lines = text.split('\n')
            for i, ln in enumerate(lines):
                if not ln.strip().startswith('|'):
                    continue
                cells = [c.strip() for c in ln.strip('|').split('|')]
                for j, cell in enumerate(cells):
                    clean = re.sub(r'\*+', '', cell).strip()
                    if any(kw in clean for kw in header_kws):
                        for nln in lines[i + 1:i + 3]:
                            if not nln.strip().startswith('|'):
                                continue
                            ncells = [c.strip() for c in nln.strip('|').split('|')]
                            if all(re.match(r'^[:\- ]+$', c) for c in ncells if c):
                                continue
                            return ncells[j] if len(ncells) > j else ''
            return ''

        def _br_items(text: str) -> List[str]:
            """Split <br/>-separated items and strip Markdown markup."""
            result = []
            for part in re.split(r'<br\s*/?>', text):
                part = re.sub(r'^\s*\*+\s*', '', part).strip()
                part = re.sub(r'\*\*([^*]+)\*\*', r'\1', part)
                if len(part) > 2:
                    result.append(part[:150])
            return result

        ta_map = self._get_competitor_ta_map()

        cards_html = ''
        for i, comp in enumerate(competitors, 1):
            name = comp.get('competitor_name', comp.get('name', f'競品{i}'))
            label = comp.get('label', comp.get('tags', ''))
            fan = (comp.get('fan_profile', '') or '')[:80]
            kws = comp.get('keywords', []) or []

            # Try to find this competitor's section in battlecard MD
            # Heading format: "### 1. 競品 Battlecard：AMG (A Message For Inner Game)"
            comp_md = ''
            if battlecard_md and name:
                pat = rf'###[^\n]*{re.escape(name)}(.*?)(?=###|\Z)'
                m = re.search(pat, battlecard_md, re.DOTALL | re.IGNORECASE)
                if m:
                    comp_md = m.group(0)

            # Extract components — try Markdown table format first, fall back to inline
            str_raw = _table_cell(comp_md, '優勢 (Strengths)', 'Strengths')
            weak_raw = _table_cell(comp_md, '劣勢 (Weaknesses)', 'Weaknesses')
            our_adv_raw = _table_cell(comp_md, '我方', 'Our Strengths')
            win_raw = _table_cell(comp_md, '我們贏', 'When We Win')
            lose_raw = _table_cell(comp_md, '我們輸', 'When We Lose')
            talking_raw = _table_cell(comp_md, '話術', '異議')

            strengths = _br_items(str_raw) or _extract_list_items(_extract_subsection(comp_md, '優勢', '強項'))
            weaknesses = _br_items(weak_raw) or _extract_list_items(_extract_subsection(comp_md, '劣勢', '弱項'))
            our_adv = _br_items(our_adv_raw) or _extract_list_items(_extract_subsection(comp_md, '我方優勢', '我們的優勢'))
            win_scenarios = (self._inline_md(re.sub(r'<br\s*/?>', '<br>', win_raw))
                             or _extract_subsection(comp_md, '我們贏的場景', '贏的場景'))[:350]
            lose_scenarios = (self._inline_md(re.sub(r'<br\s*/?>', '<br>', lose_raw))
                              or _extract_subsection(comp_md, '我們輸的場景', '輸的場景'))[:350]
            talking = (self._inline_md(re.sub(r'<br\s*/?>', '<br>', talking_raw))
                       or _extract_subsection(comp_md, '話術建議', '建議話術', '異議回應'))[:400]

            # Fallbacks
            if not strengths and kws:
                strengths = [f'關鍵字佈局：{", ".join(kws[:3])}']
            if not strengths:
                strengths = ['（請完成 Stage 5 深度分析後自動填入）']
            if not our_adv:
                our_adv = ['（請完成 Stage 5 深度分析後自動填入）']

            comp_str_html = ''.join(f'<li>{s}</li>' for s in strengths[:5])
            comp_weak_html = ''.join(f'<li class="weakness">{w}</li>' for w in weaknesses[:5])
            if not comp_weak_html:
                comp_weak_html = '<li class="weakness" style="color:#ccc;">（待分析）</li>'
            our_adv_html = ''.join(f'<li>{a}</li>' for a in our_adv[:5])

            badge = self._tier_badge(label)
            label_span = f'<span style="opacity:0.8;font-size:0.8rem;font-weight:normal;">{label[:40]}</span>' if label else ''

            scenarios_html = ''
            if win_scenarios or lose_scenarios:
                scenarios_html = f"""<div class="scenarios">
  <div class="scenario-win">
    <div class="scenario-title win-title">🟢 我們贏的場景</div>
    <div style="font-size:0.83rem;margin-top:4px;">{win_scenarios or '（待分析）'}</div>
  </div>
  <div class="scenario-lose">
    <div class="scenario-title lose-title">🔴 我們輸的場景</div>
    <div style="font-size:0.83rem;margin-top:4px;">{lose_scenarios or '（待分析）'}</div>
  </div>
</div>"""

            talking_html = ''
            if talking:
                talking_html = f"""<div class="talking-points">
  <h3>💬 建議話術</h3>
  <p>{talking}</p>
</div>"""

            # 目標客群：從 competitors.json fan_profile + 競品維度彙總表的年齡層
            comp_ta = ta_map.get(name, '')
            if not comp_ta:
                for k, v in ta_map.items():
                    if name in k or k in name:
                        comp_ta = v
                        break
            if comp_ta:
                age_m = re.search(r'\d+[-–]\d+歲', comp_ta)
                age_str = f'（{age_m.group(0)}）' if age_m else ''
                ta_display = comp_ta[:100]
                fan_html = f'<div style="margin-top:10px;font-size:0.77rem;color:#888;">目標客群{age_str}：{ta_display}</div>'
            elif fan:
                fan_html = f'<div style="margin-top:10px;font-size:0.77rem;color:#888;">目標客群：{fan}</div>'
            else:
                fan_html = ''
            kws_html = (
                f'<div style="margin-top:8px;font-size:0.77rem;color:#aaa;">主要關鍵字：{", ".join(kws[:5])}</div>'
                if kws else ''
            )

            cards_html += f"""<div class="battlecard">
  <div class="battlecard-header">
    <span>#{i} {name}</span>
    {badge}
    {label_span}
  </div>
  <div class="battlecard-body">
    <div class="battlecard-col">
      <h3>{name} 強項</h3>
      <ul>{comp_str_html}</ul>
      <h3 style="margin-top:14px;">{name} 弱項</h3>
      <ul>{comp_weak_html}</ul>
      {fan_html}
    </div>
    <div class="battlecard-col">
      <h3>{brand} 相對優勢</h3>
      <ul>{our_adv_html}</ul>
      {kws_html}
    </div>
  </div>
  {scenarios_html}
  {talking_html}
</div>
"""

        if not cards_html:
            cards_html = '<p style="color:#999;text-align:center;padding:40px;">（尚未找到競品資料，請先完成 Stage 2 競品雷達）</p>'

        logo_frag, brand_css = self._brand_customization()
        now_str = datetime.now().strftime('%Y年%m月%d日')
        data_range = self.data.get('data_range_str') or ''
        data_pill = f'<span class="meta-pill">📊 資料區間：{data_range}</span>' if data_range else ''
        body = f"""
<div class="report-header">
  {logo_frag}
  <h1>競品對決分析：{brand}</h1>
  <div class="subtitle">核心產品：{service} ｜ 共分析 {len(competitors)} 個競品</div>
  <div class="meta"><span class="meta-pill">📅 {now_str}</span>{data_pill}<span class="meta-pill">競品對決版</span></div>
</div>

<div class="section-card" style="background:#fffbf0;border-left:4px solid #e67e22;">
  <p style="font-size:0.88rem;color:#555;">
    ⚡ <strong>使用說明</strong>：此 Battlecard 協助業務團隊即時應對競品比較。
    <strong>🟢 我們贏的場景</strong>主動提出；
    <strong>🔴 我們輸的場景</strong>備妥話術轉移焦點。
    Stage 5 完成後，強項、話術欄位將自動填入 AI 分析內容。
  </p>
</div>

{cards_html}

{{review_section}}

<div class="report-footer">
  報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 系統版本：V2.0 ｜ 競品對決版<br>
  📌 按右上角「<strong>📊 下載 PPTX</strong>」可下載簡報檔，匯入 Canva / Google 簡報 / PowerPoint 即可編輯<br>
  <span style="margin-top:10px;display:inline-block;font-size:0.7rem;color:var(--ink-4);">
    <strong>方法論</strong>：資料來源為 Dcard、PTT、Google 新聞等公開管道；取樣依關鍵字與設定之時間範圍搜尋。<br>
    <strong>免責聲明</strong>：本報告供內部策略參考，數據來自公開來源與自動化擷取，請依需要驗證關鍵資訊後再行決策。
  </span>
</div>
"""

        # ── 待確認文章附錄（移自深度分析版）─────────────────────
        review_rows_all: List[tuple] = []
        for p, hdr_key in [('Dcard', 'dcard_headers'), ('PTT', 'ptt_headers'), ('Google News', 'news_headers')]:
            p_key = p.lower().replace(' ', '_') if p != 'Google News' else 'news'
            hdrs = self.data.get(hdr_key, [])
            for row in self.data.get(f'{p_key}_review_rows', []):
                d = dict(zip(hdrs, row)) if len(row) >= len(hdrs) else {}
                title = d.get('標題', '') or d.get('title', '') or ''
                link = d.get('連結', '') or d.get('文章連結', '') or d.get('link', '') or ''
                date = d.get('發布日期', '') or d.get('發佈日期', '') or d.get('published', '') or ''
                review_rows_all.append((p, title, link, date))

        if review_rows_all:
            rev_rows_html = ''
            for plat, title, link, date in review_rows_all[:100]:
                _tit = (title or "")[:80]
                title_cell = (
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'class="article-link" style="color:var(--ink-3);" aria-label="閱讀待確認文章：{_tit}">{title[:80]}</a>'
                    if link else title[:80]
                )
                rev_rows_html += (
                    f'<tr>'
                    f'<td><span class="platform-badge">{plat}</span></td>'
                    f'<td>{title_cell}</td>'
                    f'<td style="font-size:0.77rem;color:var(--ink-4);">{date}</td>'
                    f'</tr>'
                )
            review_section = f"""<div class="section-card" style="background:#FAFBFD;border-top:3px solid var(--border);">
  <h2>🔍 待確認文章（共 {len(review_rows_all)} 篇）</h2>
  <p style="font-size:0.82rem;color:var(--ink-3);margin-bottom:12px;">
    以下文章未偵測到領域關鍵字，已自動分離供人工確認。若為誤判（如競品討論但未含核心字），可忽略此篩選。
  </p>
  <table class="article-table">
    <thead><tr><th>平台</th><th>標題（可點擊查看原文）</th><th>日期</th></tr></thead>
    <tbody>{rev_rows_html}</tbody>
  </table>
</div>"""
        else:
            review_section = ''

        body = body.replace('{review_section}', review_section)

        pptx_script = self._generate_pptx_script('battlecard')
        html = self._html_page(f'競品對決 - {brand}', body,
                               extra_css=brand_css, extra_scripts=pptx_script)
        out = self.campaign_dir / 'report_battlecard.html'
        out.write_text(html, encoding='utf-8')
        try: print(f'  ✅ 競品對決版：{out.name}')
        except (ValueError, OSError): pass
        return str(out)

    # =========================================================
    #  Template 3：深度分析版
    # =========================================================

    def generate_deep_analysis(self) -> str:
        cfg = self.data.get('config', {})
        brand = cfg.get('brand', '品牌')
        service = cfg.get('service', '產品')
        industry = cfg.get('industry', '產業')
        purpose = cfg.get('purpose', '競品分析')
        audience = cfg.get('audience', '目標受眾')

        competitors = self.data.get('competitors', [])
        keywords_data = self.data.get('keywords', {})
        stats = self._get_article_stats()
        keyword_count = self._get_keyword_count()
        top_articles = self._get_top_articles(10)

        # KPI grid
        kpi_html = f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-number">{len(competitors)}</div><div class="kpi-label">競品數量</div></div>
  <div class="kpi-card"><div class="kpi-number">{stats['dcard']:,}</div><div class="kpi-label">Dcard 文章</div></div>
  <div class="kpi-card"><div class="kpi-number">{stats['ptt']:,}</div><div class="kpi-label">PTT 文章</div></div>
  <div class="kpi-card"><div class="kpi-number">{stats['news']:,}</div><div class="kpi-label">Google 新聞</div></div>
</div>"""

        # Competitor table
        comp_rows = ''
        for i, comp in enumerate(competitors, 1):
            name = comp.get('competitor_name', comp.get('name', f'競品{i}'))
            label = (comp.get('label', comp.get('tags', '')) or '')[:30]
            fan = (comp.get('fan_profile', '') or '')[:55]
            positioning = (comp.get('verification_info', comp.get('positioning', '')) or '')[:55]
            kws = ', '.join((comp.get('keywords', []) or [])[:5])
            badge = self._tier_badge(comp.get('label', '') or '')
            comp_rows += (
                f'<tr>'
                f'<td style="color:#999;font-size:0.8rem;">{i}</td>'
                f'<td><strong>{name}</strong> {badge}</td>'
                f'<td style="font-size:0.78rem;">{label}</td>'
                f'<td style="font-size:0.78rem;">{positioning}</td>'
                f'<td style="font-size:0.78rem;">{fan}</td>'
                f'<td style="font-size:0.75rem;color:#999;">{kws}</td>'
                f'</tr>'
            )
        comp_table = (
            '<table class="article-table">'
            '<thead><tr>'
            '<th>#</th><th>競品名稱</th><th>標籤</th><th>定位說明</th><th>目標客群</th><th>關鍵字</th>'
            '</tr></thead>'
            f'<tbody>{comp_rows}</tbody></table>'
        ) if comp_rows else '<p style="color:#999;">（尚無競品資料）</p>'

        # Keywords badges
        kw_html = ''
        kw_obj = keywords_data.get('keywords', keywords_data)
        if isinstance(kw_obj, dict):
            for cat, kws in kw_obj.items():
                if isinstance(kws, list) and kws:
                    badges = ''.join(
                        f'<span style="display:inline-block;background:#e8f0fd;color:#2d6a9f;'
                        f'padding:3px 10px;border-radius:12px;margin:3px;font-size:0.78rem;">{k}</span>'
                        for k in kws
                    )
                    kw_html += (
                        f'<div style="margin-bottom:14px;">'
                        f'<div style="font-size:0.83rem;color:#7f8c8d;margin-bottom:4px;font-weight:bold;">{cat}</div>'
                        f'{badges}</div>'
                    )

        # Top articles table
        art_rows = ''
        for a in top_articles:
            link = a.get('link', '')
            _tit = (a.get("title") or "")[:80]
            title_cell = (
                f'<a href="{link}" target="_blank" rel="noopener noreferrer" class="article-link" style="font-size:0.82rem;" aria-label="閱讀文章：{_tit}">{a["title"]}</a>'
                if link else f'<span style="font-size:0.82rem;">{a["title"]}</span>'
            )
            art_rows += (
                f'<tr>'
                f'<td><span class="platform-badge">{a["platform"]}</span></td>'
                f'<td>{title_cell}</td>'
                f'<td>{a["board"]}</td>'
                f'<td class="engagement" style="white-space:nowrap;">{a.get("comment_str", "-")}</td>'
                f'<td style="white-space:nowrap;font-size:0.78rem;">{a["date"]}</td>'
                f'</tr>'
            )
        art_section = (
            '<div class="section-card"><h2>📰 高互動社群文章 TOP 10</h2>'
            '<table class="article-table">'
            '<thead><tr><th>平台</th><th>標題（可點擊）</th><th>看板</th><th>留言數</th><th>日期</th></tr></thead>'
            f'<tbody>{art_rows}</tbody></table></div>'
        ) if art_rows else ''

        # AI Sections rendered as HTML
        deep_md = self.data.get('deep_analysis_md', '')
        industry_md = self.data.get('industry_scan_md', '')

        deep_html = self._md_to_html(deep_md) if deep_md else (
            '<p style="color:#999;">（Stage 5 深度分析尚未執行）</p>'
        )
        # 產業掃描：圖表可視化 + 原始 Markdown 內文
        industry_viz_html = self._render_industry_viz(industry_md)
        industry_raw_html = self._md_to_html(industry_md) if industry_md else (
            '<p style="color:#999;">（Stage 1 產業掃描尚未執行）</p>'
        )
        industry_html = industry_viz_html + industry_raw_html

        logo_frag, brand_css = self._brand_customization()
        now_str = datetime.now().strftime('%Y年%m月%d日')
        data_range = self.data.get('data_range_str') or ''
        data_pill = f'<span class="meta-pill">📊 資料區間：{data_range}</span>' if data_range else ''
        body = f"""
<div class="report-header">
  {logo_frag}
  <h1>深度競品分析報告：{brand}</h1>
  <div class="subtitle">{purpose} ｜ {industry} ｜ 核心產品：{service}</div>
  <div class="meta"><span class="meta-pill">📅 {now_str}</span><span class="meta-pill">👤 {audience}</span>{data_pill}<span class="meta-pill">深度分析版</span></div>
</div>

{kpi_html}

<div class="section-card">
  <h2>🎯 完整競品清單（{len(competitors)} 個）</h2>
  {comp_table}
</div>

<div class="section-card">
  <h2>🔑 關鍵字策略（共 {keyword_count} 個）</h2>
  {kw_html or '<p style="color:#999;">（關鍵字資料尚未載入）</p>'}
</div>

{art_section}

<div class="section-card">
  <h2>🏭 產業掃描（Stage 1 AI 分析）</h2>
  <div class="md-content">{industry_html}</div>
</div>

<div class="section-card">
  <h2>🧠 深度分析（Stage 5 AI 分析 - PMM 框架）</h2>
  <p style="font-size:0.8rem;color:#999;margin-bottom:14px;">
    包含：競品維度彙總、SWOT 矩陣、Battlecard、消費者痛點、市場機會缺口、定位聲明、行銷策略、風險評估
  </p>
  <div class="md-content">{deep_html}</div>
</div>

<div class="report-footer">
  報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 系統版本：V2.0 ｜ 深度分析版<br>
  📌 Ctrl + P → 另存 PDF｜建議使用 A4 橫向列印或縮放至 80%<br>
  <span style="margin-top:10px;display:inline-block;font-size:0.7rem;color:var(--ink-4);">
    <strong>方法論</strong>：資料來源為 Dcard、PTT、Google 新聞等公開管道；取樣依關鍵字與時間範圍搜尋，AI 分析基於上述資料產出。<br>
    <strong>免責聲明</strong>：本報告供內部策略參考，數據來自公開來源與自動化擷取，請依需要驗證關鍵資訊後再行決策。
  </span>
</div>
"""

        # 新：情緒趨勢圖 + 競品評分矩陣
        timeline_section  = self._render_sentiment_timeline()
        scorecard_section = self._render_scorecard_section()
        if timeline_section or scorecard_section:
            extra_blocks = '\n\n'.join(s for s in [timeline_section, scorecard_section] if s)
            body = body.replace(
                '<div class="section-card">\n  <h2>🏭 產業掃描',
                extra_blocks + '\n\n<div class="section-card">\n  <h2>🏭 產業掃描',
            )

        html = self._html_page(f'深度分析 - {brand} 競品分析', body, extra_css=brand_css)
        out = self.campaign_dir / 'report_deep_analysis.html'
        out.write_text(html, encoding='utf-8')
        try: print(f'  ✅ 深度分析版：{out.name}')
        except (ValueError, OSError): pass
        return str(out)

    # =========================================================
    #  主入口：生成全部模板
    # =========================================================

    def generate_all(self) -> Dict[str, str]:
        """生成三份 HTML 報告，回傳 {key: file_path} dict。"""
        print('\n📄 V2 HTML 報告生成器啟動...')
        self.load_all_data()

        outputs: Dict[str, str] = {}
        outputs['executive'] = self.generate_executive_summary()
        outputs['battlecard'] = self.generate_battlecard()
        outputs['deep_analysis'] = self.generate_deep_analysis()

        print(f'\n✅ 三份報告已生成於：{self.campaign_dir}')
        print('   📌 在 Chrome 開啟 HTML 檔案，按 Ctrl+P → 另存 PDF 可匯入 Canva / Google 簡報')
        return outputs


# =========================================================
#  便捷函式 & 命令列入口
# =========================================================

def generate_html_reports(campaign_dir: str) -> Dict[str, str]:
    """從 orchestrator 呼叫的便捷函式。"""
    return HtmlReportGenerator(campaign_dir).generate_all()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法：python html_report_generator.py <campaign_dir>')
        print('範例：python html_report_generator.py reports/campaign_20260301_1430')
        sys.exit(1)
    results = generate_html_reports(sys.argv[1])
    print('\n產出檔案：')
    for key, path in results.items():
        print(f'  {key}: {path}')
