# -*- coding: utf-8 -*-
"""
P2.2 圖表強化模組
功能：
- 情緒趨勢圖（時間軸折線圖）
- 情緒雷達圖（6維度）
- 關鍵字文字雲
- 平台情緒比較長條圖

輸出：PNG 圖檔 + JSON 原始數據
"""

import json
import os
import random
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# 設定中文字型
matplotlib.rcParams['font.sans-serif'] = [
    'Noto Sans CJK TC', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei',
    'Microsoft JhengHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans'
]
matplotlib.rcParams['axes.unicode_minus'] = False

# 顏色配置
COLORS = {
    'background': '#1a1a2e',
    'text': '#ffffff',
    'positive': '#4CAF50',    # 綠色
    'negative': '#F44336',    # 紅色
    'neutral': '#9E9E9E',     # 灰色
    'anger': '#FF5722',
    'joy': '#FFEB3B',
    'sadness': '#2196F3',
    'surprise': '#9C27B0',
    'fear': '#795548',
    'disgust': '#607D8B',
    'dcard': '#FF6B6B',
    'instagram': '#E1306C',
    'facebook': '#4267B2',
    'youtube': '#FF0000',
    'threads': '#0081FF',
    'ptt': '#00B140',
}

# 確保輸出目錄存在
OUTPUT_DIR = "charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def _setup_dark_style():
    """設定深色風格"""
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': COLORS['background'],
        'axes.facecolor': COLORS['background'],
        'axes.edgecolor': '#ffffff',
        'axes.labelcolor': '#ffffff',
        'text.color': '#ffffff',
        'xtick.color': '#ffffff',
        'ytick.color': '#ffffff',
        'grid.color': '#333333',
        'grid.alpha': 0.3,
    })


def generate_sentiment_trend(
    data: List[Dict],
    time_col: str = "date",
    time_group: str = "day",
    platforms: List[str] = None,
    output_dir: str = OUTPUT_DIR
) -> Tuple[str, str]:
    """
    生成情緒趨勢圖（時間軸折線圖）
    
    參數：
    - data: 資料列表，每筆需包含 {date, sentiment_scores: {positive, negative, neutral}}
    - time_col: 日期欄位名稱
    - time_group: 時間分組（day/week/month）
    - platforms: 平台列表（可選，用於多平台比較）
    - output_dir: 輸出目錄
    
    回傳：(png_path, json_path)
    """
    _setup_dark_style()
    
    # 處理時間分組
    def group_date(date_str: str) -> str:
        try:
            if isinstance(date_str, str):
                date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            else:
                date = date_str
            
            if time_group == "week":
                # 每週第一天
                return (date - timedelta(days=date.weekday())).strftime("%Y-%W")
            elif time_group == "month":
                return date.strftime("%Y-%m")
            else:
                return date.strftime("%Y-%m-%d")
        except:
            return "unknown"
    
    # 按時間分組計算平均情緒
    trend_data = {}
    for item in data:
        group = group_date(item.get(time_col, ""))
        if group == "unknown":
            continue
        
        scores = item.get("scores", {})
        if group not in trend_data:
            trend_data[group] = {"positive": [], "negative": [], "neutral": []}
        
        trend_data[group]["positive"].append(scores.get("positive", 0))
        trend_data[group]["negative"].append(scores.get("negative", 0))
        trend_data[group]["neutral"].append(scores.get("neutral", 0))
    
    # 計算平均值
    sorted_dates = sorted(trend_data.keys())
    dates = []
    pos_scores = []
    neg_scores = []
    neu_scores = []
    
    for d in sorted_dates:
        dates.append(d)
        pos_scores.append(np.mean(trend_data[d]["positive"]) * 100)
        neg_scores.append(np.mean(trend_data[d]["negative"]) * 100)
        neu_scores.append(np.mean(trend_data[d]["neutral"]) * 100)
    
    # 繪圖
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(COLORS['background'])
    
    x = range(len(dates))
    ax.plot(x, pos_scores, marker='o', linewidth=2, color=COLORS['positive'], label='正面 Positive')
    ax.plot(x, neg_scores, marker='s', linewidth=2, color=COLORS['negative'], label='負面 Negative')
    ax.plot(x, neu_scores, marker='^', linewidth=2, color=COLORS['neutral'], label='中性 Neutral')
    
    ax.set_xlabel('時間', fontsize=12)
    ax.set_ylabel('情緒分數 (%)', fontsize=12)
    ax.set_title('情緒趨勢分析', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.legend(loc='upper right', framealpha=0.3)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)
    
    plt.tight_layout()
    
    ts = get_timestamp()
    png_path = os.path.join(output_dir, f"sentiment_trend_{ts}.png")
    json_path = os.path.join(output_dir, f"sentiment_trend_{ts}.json")
    
    plt.savefig(png_path, dpi=150, facecolor=COLORS['background'])
    plt.close()
    
    # 儲存 JSON
    json_data = {
        "time_group": time_group,
        "dates": dates,
        "positive": pos_scores,
        "negative": neg_scores,
        "neutral": neu_scores,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return png_path, json_path


def generate_emotion_radar(
    data: List[Dict],
    compare_data: List[Dict] = None,
    output_dir: str = OUTPUT_DIR
) -> Tuple[str, str]:
    """
    生成情緒雷達圖（6維度）
    
    參數：
    - data: 情緒資料列表，每筆需包含 {emotion_counts: {anger, joy, sadness, surprise, fear, disgust}}
    - compare_data: 對照組資料（可選，用於比較兩個時間段）
    - output_dir: 輸出目錄
    
    回傳：(png_path, json_path)
    """
    _setup_dark_style()
    
    emotions = ["anger", "joy", "sadness", "surprise", "fear", "disgust"]
    emotion_labels = {
        "anger": "憤怒",
        "joy": "開心",
        "sadness": "悲傷",
        "surprise": "驚訝",
        "fear": "恐懼",
        "disgust": "厭惡",
    }
    
    # 計算情緒分佈
    def calc_emotion_scores(data_list: List[Dict]) -> List[float]:
        counts = {e: 0 for e in emotions}
        total = 0
        for item in data_list:
            emo_counts = item.get("emotion_counts", {})
            for e in emotions:
                counts[e] += emo_counts.get(e, 0)
                total += emo_counts.get(e, 0)
        
        if total == 0:
            return [0] * 6
        
        return [counts[e] / total * 100 for e in emotions]
    
    scores1 = calc_emotion_scores(data)
    scores2 = calc_emotion_scores(compare_data) if compare_data else None
    
    # 雷達圖
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')
    
    angles = np.linspace(0, 2 * np.pi, len(emotions), endpoint=False).tolist()
    angles += angles[:1]
    
    # 第一組資料
    scores1_plot = scores1 + scores1[:1]
    ax.plot(angles, scores1_plot, 'o-', linewidth=2, color=COLORS['dcard'], label='本期')
    ax.fill(angles, scores1_plot, alpha=0.25, color=COLORS['dcard'])
    
    # 比較組（如果有）
    if scores2:
        scores2_plot = scores2 + scores2[:1]
        ax.plot(angles, scores2_plot, 's--', linewidth=2, color=COLORS['youtube'], label='上期')
        ax.fill(angles, scores2_plot, alpha=0.15, color=COLORS['youtube'])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f"{emotion_labels[e]}\n{e}" for e in emotions], fontsize=10)
    ax.set_ylim(0, max(max(scores1), max(scores2 or [0])) * 1.2)
    ax.set_title('情緒分析雷達圖', fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax.grid(True)
    
    plt.tight_layout()
    
    ts = get_timestamp()
    png_path = os.path.join(output_dir, f"emotion_radar_{ts}.png")
    json_path = os.path.join(output_dir, f"emotion_radar_{ts}.json")
    
    plt.savefig(png_path, dpi=150, facecolor=COLORS['background'])
    plt.close()
    
    # JSON
    json_data = {
        "current_period": {e: round(scores1[i], 2) for i, e in enumerate(emotions)},
    }
    if scores2:
        json_data["previous_period"] = {e: round(scores2[i], 2) for i, e in enumerate(emotions)}
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return png_path, json_path


def generate_wordcloud(
    data: List[Dict],
    text_col: str = "content",
    positive_keywords: List[str] = None,
    negative_keywords: List[str] = None,
    output_dir: str = OUTPUT_DIR
) -> str:
    """
    生成關鍵字文字雲
    
    參數：
    - data: 資料列表
    - text_col: 文字欄位名稱
    - positive_keywords: 正面關鍵詞列表（用於標記顏色）
    - negative_keywords: 負面關鍵詞列表（用於標記顏色）
    - output_dir: 輸出目錄
    
    回傳：png_path
    """
    try:
        from wordcloud import WordCloud
    except ImportError:
        print("⚠️ 請安裝 wordcloud：pip install wordcloud")
        return None
    
    # 預設關鍵詞
    if positive_keywords is None:
        positive_keywords = ["推薦", "好用", "棒", "讚", "超棒", "必買", "推薦", "喜歡", "滿意"]
    if negative_keywords is None:
        negative_keywords = ["雷", "爛", "踩雷", "退貨", "失望", "不推", "貴", "騙", "垃圾"]
    
    # 收集所有文字
    all_text = ""
    for item in data:
        text = item.get(text_col, "")
        if text:
            all_text += " " + text
    
    if not all_text.strip():
        print("⚠️ 沒有文字資料可生成文字雲")
        return None
    
    # 建立顏色函式
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        word_lower = word.lower()
        
        # 檢查是否為負面詞
        for nw in negative_keywords:
            if nw in word_lower:
                return f"hsl(0, 70%, 50%)"  # 紅色
        
        # 檢查是否為正面詞
        for pw in positive_keywords:
            if pw in word_lower:
                return f"hsl(120, 70%, 50%)"  # 綠色
        
        # 預設灰色
        return f"hsl(0, 0%, 70%)"
    
    # 嘗試設定中文字型
    font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msjh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        '/System/Library/Fonts/PingFang.ttc',
    ]
    
    font_path = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break
    
    # 生成文字雲
    wc = WordCloud(
        font_path=font_path,
        width=1200,
        height=800,
        background_color=COLORS['background'],
        max_words=100,
        color_func=color_func,
        prefer_horizontal=0.7,
        min_font_size=10,
    )
    
    wc.generate(all_text)
    
    ts = get_timestamp()
    png_path = os.path.join(output_dir, f"wordcloud_{ts}.png")
    
    plt.figure(figsize=(14, 8))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title('關鍵字文字雲', fontsize=16, fontweight='bold', color='#ffffff', pad=20)
    plt.tight_layout()
    
    plt.savefig(png_path, dpi=150, facecolor=COLORS['background'])
    plt.close()
    
    return png_path


def generate_platform_comparison(
    platform_data: Dict[str, List[Dict]],
    output_dir: str = OUTPUT_DIR
) -> Tuple[str, str]:
    """
    生成平台情緒比較長條圖
    
    參數：
    - platform_data: 字典 {平台名稱: [情緒資料列表]}
      例如: {"dcard": [...], "instagram": [...], "facebook": [...], "youtube": [...]}
    - output_dir: 輸出目錄
    
    回傳：(png_path, json_path)
    """
    _setup_dark_style()
    
    platforms = list(platform_data.keys())
    platform_colors = {
        "dcard": COLORS['dcard'],
        "instagram": COLORS['instagram'],
        "facebook": COLORS['facebook'],
        "youtube": COLORS['youtube'],
        "threads": COLORS['threads'],
        "ptt": COLORS['ptt'],
    }
    
    # 計算每個平台的平均情緒分數
    pos_scores = []
    neg_scores = []
    neu_scores = []
    
    for platform in platforms:
        data = platform_data.get(platform, [])
        if not data:
            pos_scores.append(0)
            neg_scores.append(0)
            neu_scores.append(0)
            continue
        
        pos = np.mean([d.get("scores", {}).get("positive", 0) for d in data]) * 100
        neg = np.mean([d.get("scores", {}).get("negative", 0) for d in data]) * 100
        neu = np.mean([d.get("scores", {}).get("neutral", 0) for d in data]) * 100
        
        pos_scores.append(round(pos, 1))
        neg_scores.append(round(neg, 1))
        neu_scores.append(round(neu, 1))
    
    # 繪圖
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(COLORS['background'])
    
    x = np.arange(len(platforms))
    width = 0.25
    
    bars1 = ax.bar(x - width, pos_scores, width, label='正面', color=COLORS['positive'])
    bars2 = ax.bar(x, neg_scores, width, label='負面', color=COLORS['negative'])
    bars3 = ax.bar(x + width, neu_scores, width, label='中性', color=COLORS['neutral'])
    
    ax.set_xlabel('平台', fontsize=12)
    ax.set_ylabel('百分比 (%)', fontsize=12)
    ax.set_title('各平台情緒分佈比較', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(platforms)
    ax.legend(loc='upper right', framealpha=0.3)
    ax.grid(True, axis='y', alpha=0.3)
    ax.set_ylim(0, 100)
    
    # 在長條上顯示數值
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}%',
                       ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    ts = get_timestamp()
    png_path = os.path.join(output_dir, f"platform_comparison_{ts}.png")
    json_path = os.path.join(output_dir, f"platform_comparison_{ts}.json")
    
    plt.savefig(png_path, dpi=150, facecolor=COLORS['background'])
    plt.close()
    
    # JSON
    json_data = {
        platform: {
            "positive": pos_scores[i],
            "negative": neg_scores[i],
            "neutral": neu_scores[i],
        }
        for i, platform in enumerate(platforms)
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return png_path, json_path


def generate_competitor_radar(
    competitor_data: Dict[str, Dict],
    dimensions: List[str] = None,
    output_dir: str = OUTPUT_DIR
) -> Tuple[str, str]:
    """
    生成競品比較雷達圖
    
    參數：
    - competitor_data: 字典 {品牌名稱: {維度: 分數}}
      例如: {"品牌A": {"聲量": 80, "正面": 70, "負面": 20, "互動率": 60}}
    - dimensions: 維度名稱列表
    - output_dir: 輸出目錄
    
    回傳：(png_path, json_path)
    """
    _setup_dark_style()
    
    if dimensions is None:
        dimensions = ["聲量", "正面評價", "負面評價", "互動率", "趨勢"]
    
    competitor_colors = [
        COLORS['dcard'], COLORS['instagram'], COLORS['facebook'],
        COLORS['youtube'], COLORS['positive'], COLORS['negative']
    ]
    
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')
    
    angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
    angles += angles[:1]
    
    for idx, (competitor, scores) in enumerate(competitor_data.items()):
        values = [scores.get(d, 0) for d in dimensions]
        values += values[:1]
        
        color = competitor_colors[idx % len(competitor_colors)]
        ax.plot(angles, values, 'o-', linewidth=2, color=color, label=competitor)
        ax.fill(angles, values, alpha=0.1, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title('競品比較雷達圖', fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax.grid(True)
    
    plt.tight_layout()
    
    ts = get_timestamp()
    png_path = os.path.join(output_dir, f"competitor_radar_{ts}.png")
    json_path = os.path.join(output_dir, f"competitor_radar_{ts}.json")
    
    plt.savefig(png_path, dpi=150, facecolor=COLORS['background'])
    plt.close()
    
    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(competitor_data, f, ensure_ascii=False, indent=2)
    
    return png_path, json_path


# ===========================================
# 測試入口
# ===========================================

if __name__ == "__main__":
    # 測試資料
    test_trend_data = [
        {"date": "2024-01-01", "scores": {"positive": 0.6, "negative": 0.2, "neutral": 0.2}},
        {"date": "2024-01-02", "scores": {"positive": 0.5, "negative": 0.3, "neutral": 0.2}},
        {"date": "2024-01-03", "scores": {"positive": 0.4, "negative": 0.4, "neutral": 0.2}},
        {"date": "2024-01-04", "scores": {"positive": 0.7, "negative": 0.1, "neutral": 0.2}},
        {"date": "2024-01-05", "scores": {"positive": 0.3, "negative": 0.5, "neutral": 0.2}},
    ]
    
    test_emotion_data = [
        {"emotion_counts": {"anger": 10, "joy": 30, "sadness": 5, "surprise": 8, "fear": 2, "disgust": 3}},
        {"emotion_counts": {"anger": 15, "joy": 25, "sadness": 8, "surprise": 10, "fear": 3, "disgust": 5}},
    ]
    
    test_platform_data = {
        "dcard": [{"scores": {"positive": 0.4, "negative": 0.3, "neutral": 0.3}}] * 10,
        "instagram": [{"scores": {"positive": 0.6, "negative": 0.1, "neutral": 0.3}}] * 10,
        "facebook": [{"scores": {"positive": 0.3, "negative": 0.4, "neutral": 0.3}}] * 10,
        "youtube": [{"scores": {"positive": 0.5, "negative": 0.2, "neutral": 0.3}}] * 10,
    }
    
    test_text_data = [
        {"content": "這產品太棒了，超級推薦！必買神器"},
        {"content": "踩雷了，退貨還要自己出運費，根本垃圾"},
        {"content": "還不錯，CP值滿高的"},
    ]
    
    print("=" * 50)
    print("P2.2 圖表強化測試")
    print("=" * 50)
    
    # 測試趨勢圖
    print("\n[1] 生成情緒趨勢圖...")
    png, json_file = generate_sentiment_trend(test_trend_data)
    print(f"    ✓ PNG: {png}")
    print(f"    ✓ JSON: {json_file}")
    
    # 測試雷達圖
    print("\n[2] 生成情緒雷達圖...")
    png, json_file = generate_emotion_radar(test_emotion_data)
    print(f"    ✓ PNG: {png}")
    print(f"    ✓ JSON: {json_file}")
    
    # 測試文字雲
    print("\n[3] 生成關鍵字文字雲...")
    png = generate_wordcloud(test_text_data)
    print(f"    ✓ PNG: {png}")
    
    # 測試平台比較
    print("\n[4] 生成平台情緒比較...")
    png, json_file = generate_platform_comparison(test_platform_data)
    print(f"    ✓ PNG: {png}")
    print(f"    ✓ JSON: {json_file}")
    
    print("\n✅ 所有圖表測試完成！")
