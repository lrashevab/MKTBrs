# -*- coding: utf-8 -*-
"""
視覺化圖表生成器：競品矩陣、情緒雷達圖、趨勢圖
"""

import json
import pandas as pd  # type: ignore[reportMissingImports]
import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
import matplotlib  # type: ignore[reportMissingImports]
from pathlib import Path
from typing import List, Dict

from logger import get_logger

# 設定中文字型
matplotlib.rc('font', family='Microsoft JhengHei')
plt.rcParams['axes.unicode_minus'] = False

logger = get_logger("visualizer")

class ChartGenerator:
    """圖表生成器"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)
    
    def generate_competitor_matrix(self, competitors: List[Dict]) -> str:
        """
        生成競品矩陣圖（價格 vs 聲量）
        """
        logger.info("📊 生成競品矩陣圖...")
        
        # 提取數據
        names = []
        prices = []
        volumes = []
        
        for comp in competitors[:15]:  # 最多 15 個
            name = comp.get('name', '未知')
            
            # 價格評分（簡化版）
            price_str = comp.get('price_range', '中')
            price_map = {'低': 1, '中低': 2, '中': 3, '中高': 4, '高': 5}
            price = price_map.get(price_str, 3)
            
            # 聲量評分（隨機生成，實際應從輿情數據計算）
            import random
            volume = random.randint(1, 10)
            
            names.append(name)
            prices.append(price)
            volumes.append(volume)
        
        # 繪圖
        fig, ax = plt.subplots(figsize=(12, 8))
        
        scatter = ax.scatter(prices, volumes, s=300, alpha=0.6, c=range(len(names)), cmap='viridis')
        
        # 標註品牌名稱
        for i, name in enumerate(names):
            ax.annotate(name, (prices[i], volumes[i]), 
                       fontsize=9, ha='center', va='bottom')
        
        # 設定軸標籤
        ax.set_xlabel('價格定位 (1=低價, 5=高價)', fontsize=12)
        ax.set_ylabel('市場聲量 (1=低, 10=高)', fontsize=12)
        ax.set_title('競品定位矩陣圖', fontsize=16, fontweight='bold')
        
        # 加入象限線
        ax.axhline(y=5.5, color='gray', linestyle='--', alpha=0.3)
        ax.axvline(x=3, color='gray', linestyle='--', alpha=0.3)
        
        # 象限標籤
        ax.text(1.5, 9, '低價高聲量', fontsize=10, alpha=0.5)
        ax.text(4, 9, '高價高聲量', fontsize=10, alpha=0.5)
        ax.text(1.5, 1.5, '低價低聲量', fontsize=10, alpha=0.5)
        ax.text(4, 1.5, '高價低聲量', fontsize=10, alpha=0.5)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_file = self.charts_dir / "competitor_matrix.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 競品矩陣圖已生成：{output_file}")
        return str(output_file)
    
    def generate_sentiment_radar(self, sentiment_data: Dict) -> str:
        """
        生成四維度情緒雷達圖
        """
        logger.info("📊 生成情緒雷達圖...")

        import numpy as np  # type: ignore[reportMissingImports]

        # 四維度（示例數據）
        categories = ['產品技術觀感', '情緒焦慮', '商業消費爭議', '期待正向需求']
        values = [7, 5, 3, 8]  # 實際應從 sentiment_data 計算
        
        # 閉合雷達圖
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values, 'o-', linewidth=2, color='#3498db')
        ax.fill(angles, values, alpha=0.25, color='#3498db')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12)
        ax.set_ylim(0, 10)
        ax.set_title('輿情四維度分析', fontsize=16, fontweight='bold', pad=20)
        
        ax.grid(True)
        
        output_file = self.charts_dir / "sentiment_radar.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 情緒雷達圖已生成：{output_file}")
        return str(output_file)
    
    def generate_trend_chart(self, df: pd.DataFrame, date_col: str = '發布日期') -> str:
        """
        生成輿情趨勢圖
        """
        logger.info("📊 生成輿情趨勢圖...")
        
        # 轉換日期格式
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        
        # 按日期統計
        daily_counts = df.groupby(df[date_col].dt.date).size()
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        ax.plot(daily_counts.index, daily_counts.values, marker='o', linewidth=2, color='#e74c3c')
        ax.fill_between(daily_counts.index, daily_counts.values, alpha=0.3, color='#e74c3c')
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('文章數量', fontsize=12)
        ax.set_title('社群討論趨勢', fontsize=16, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_file = self.charts_dir / "trend_chart.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ 趨勢圖已生成：{output_file}")
        return str(output_file)
    
    def generate_all_charts(self, campaign_dir: str) -> Dict[str, str]:
        """生成所有圖表"""
        charts = {}
        
        # 讀取競品資料
        competitors_file = Path(campaign_dir) / "competitors.json"
        if competitors_file.exists():
            with open(competitors_file, 'r', encoding='utf-8') as f:
                competitors = json.load(f)
            charts['matrix'] = self.generate_competitor_matrix(competitors)
        
        # 生成雷達圖
        charts['radar'] = self.generate_sentiment_radar({})
        
        # 讀取 Dcard 數據生成趨勢圖
        dcard_files = list(Path(campaign_dir).glob("dcard_*.csv"))
        if dcard_files:
            df = pd.read_csv(dcard_files[0])
            charts['trend'] = self.generate_trend_chart(df)
        
        return charts
