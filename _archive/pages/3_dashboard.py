# -*- coding: utf-8 -*-
"""
圖表儀表板頁面 - Dashboard
"""

import os
import sys
import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show():
    st.title("📈 圖表儀表板")
    st.markdown("視覺化分析結果")
    st.markdown("---")
    
    # 檢查是否有資料
    if not st.session_state.sentiment_results:
        st.warning("尚無分析結果，請先完成「情緒分析」")
        return
    
    results_df = st.session_state.sentiment_results
    
    # 側邊欄設定
    with st.sidebar:
        st.markdown("### ⚙️ 圖表設定")
        
        # 圖表選擇
        chart_types = st.multiselect(
            "選擇要顯示的圖表",
            [
                "情緒趨勢圖",
                "情緒雷達圖",
                "關鍵字文字雲",
                "平台情緒比較",
                "競品雷達圖"
            ],
            default=[
                "情緒趨勢圖",
                "情緒雷達圖",
                "關鍵字文字雲",
                "平台情緒比較"
            ]
        )
        
        # 時間分組
        time_group = st.selectbox(
            "時間分組",
            ["按天", "按週", "按月"],
            index=0
        )
        
        time_group_map = {"按天": "day", "按週": "week", "按月": "month"}
        
        generate_btn = st.button("🎨 產生圖表", type="primary", use_container_width=True)
    
    # 準備資料
    def prepare_trend_data(df):
        """準備趨勢圖資料"""
        data = []
        
        date_col = None
        for col in ["date", "發布日期", "published_at", "時間"]:
            if col in df.columns:
                date_col = col
                break
        
        if not date_col:
            return None
        
        for _, row in df.iterrows():
            data.append({
                "date": str(row.get(date_col, "")),
                "scores": {
                    "positive": row.get("positive_score", 0),
                    "negative": row.get("negative_score", 0),
                    "neutral": row.get("neutral_score", 0),
                }
            })
        
        return data
    
    def prepare_emotion_data(df):
        """準備雷達圖資料"""
        data = []
        
        if "emotion" in df.columns:
            emotion_counts = df["emotion"].value_counts().to_dict()
            data.append({
                "emotion_counts": {k: v for k, v in emotion_counts.items() if k != "none"}
            })
        
        return data
    
    def prepare_text_data(df):
        """準備文字雲資料"""
        data = []
        
        content_col = None
        for col in ["content", "text", "貼文內容", "文章內容"]:
            if col in df.columns:
                content_col = col
                break
        
        if content_col:
            for _, row in df.iterrows():
                text = str(row.get(content_col, ""))
                if text and text != "nan":
                    data.append({"content": text})
        
        return data
    
    def prepare_platform_data(df):
        """準備平台比較資料"""
        platform_data = {}
        
        if "platform" in df.columns:
            for platform in df["platform"].unique():
                platform_df = df[df["platform"] == platform]
                platform_data[platform] = []
                
                for _, row in platform_df.iterrows():
                    platform_data[platform].append({
                        "scores": {
                            "positive": row.get("positive_score", 0),
                            "negative": row.get("negative_score", 0),
                            "neutral": row.get("neutral_score", 0),
                        }
                    })
        
        return platform_data
    
    # 產生圖表
    if generate_btn:
        from chart_generator import (
            generate_sentiment_trend,
            generate_emotion_radar,
            generate_wordcloud,
            generate_platform_comparison,
            generate_competitor_radar,
        )
        
        # 確保輸出目錄存在
        os.makedirs("charts", exist_ok=True)
        
        progress_bar = st.progress(0)
        
        # 情緒趨勢圖
        if "情緒趨勢圖" in chart_types:
            st.markdown("### 📈 情緒趨勢圖")
            
            trend_data = prepare_trend_data(results_df)
            if trend_data:
                try:
                    png_path, json_path = generate_sentiment_trend(
                        trend_data,
                        time_group=time_group_map[time_group]
                    )
                    st.image(png_path, use_container_width=True)
                    
                    # 下載按鈕
                    with open(png_path, "rb") as f:
                        st.download_button(
                            "⬇️ 下載 PNG",
                            f.read(),
                            "sentiment_trend.png",
                            "image/png"
                        )
                except Exception as e:
                    st.error(f"產生趨勢圖失敗：{str(e)}")
            else:
                st.warning("缺少日期欄位，無法產生趨勢圖")
            
            st.markdown("---")
            
            progress_bar.progress(20)
        
        # 情緒雷達圖
        if "情緒雷達圖" in chart_types:
            st.markdown("### 🎯 情緒雷達圖")
            
            emotion_data = prepare_emotion_data(results_df)
            
            if emotion_data:
                try:
                    png_path, json_path = generate_emotion_radar(emotion_data)
                    st.image(png_path, use_container_width=True)
                    
                    with open(png_path, "rb") as f:
                        st.download_button(
                            "⬇️ 下載 PNG",
                            f.read(),
                            "emotion_radar.png",
                            "image/png"
                        )
                except Exception as e:
                    st.error(f"產生雷達圖失敗：{str(e)}")
            else:
                st.warning("缺少情緒資料，無法產生雷達圖")
            
            st.markdown("---")
            
            progress_bar.progress(40)
        
        # 關鍵字文字雲
        if "關鍵字文字雲" in chart_types:
            st.markdown("### ☁️ 關鍵字文字雲")
            
            text_data = prepare_text_data(results_df)
            
            if text_data:
                try:
                    png_path = generate_wordcloud(text_data)
                    if png_path:
                        st.image(png_path, use_container_width=True)
                        
                        with open(png_path, "rb") as f:
                            st.download_button(
                                "⬇️ 下載 PNG",
                                f.read(),
                                "wordcloud.png",
                                "image/png"
                            )
                    else:
                        st.warning("無法產生文字雲")
                except Exception as e:
                    st.error(f"產生文字雲失敗：{str(e)}")
            else:
                st.warning("缺少文字資料，無法產生文字雲")
            
            st.markdown("---")
            
            progress_bar.progress(60)
        
        # 平台情緒比較
        if "平台情緒比較" in chart_types:
            st.markdown("### 📊 平台情緒比較")
            
            platform_data = prepare_platform_data(results_df)
            
            if platform_data:
                try:
                    png_path, json_path = generate_platform_comparison(platform_data)
                    st.image(png_path, use_container_width=True)
                    
                    with open(png_path, "rb") as f:
                        st.download_button(
                            "⬇️ 下載 PNG",
                            f.read(),
                            "platform_comparison.png",
                            "image/png"
                        )
                except Exception as e:
                    st.error(f"產生平台比較圖失敗：{str(e)}")
            else:
                st.warning("缺少平台資料，無法產生比較圖")
            
            st.markdown("---")
            
            progress_bar.progress(80)
        
        # 競品雷達圖
        if "競品雷達圖" in chart_types:
            st.markdown("### 🏆 競品雷達圖")
            
            # 讓使用者輸入競品資料
            st.info("💡 請輸入競品比較維度分數（0-100）")
            
            competitor_input = st.text_area(
                "輸入競品資料（JSON格式）",
                placeholder='''{
    "品牌A": {"聲量": 80, "正面評價": 70, "負面評價": 20, "互動率": 60, "趨勢": 75},
    "品牌B": {"聲量": 60, "正面評價": 50, "負面評價": 30, "互動率": 80, "趨勢": 65}
}''',
                height=150
            )
            
            if competitor_input:
                try:
                    competitor_data = json.loads(competitor_input)
                    
                    png_path, json_path = generate_competitor_radar(competitor_data)
                    st.image(png_path, use_container_width=True)
                    
                    with open(png_path, "rb") as f:
                        st.download_button(
                            "⬇️ 下載 PNG",
                            f.read(),
                            "competitor_radar.png",
                            "image/png"
                        )
                except json.JSONDecodeError:
                    st.error("JSON 格式錯誤")
                except Exception as e:
                    st.error(f"產生競品雷達圖失敗：{str(e)}")
            
            st.markdown("---")
            
            progress_bar.progress(100)
        
        st.success("✅ 所有圖表產生完成！")
    
    # 說明
    st.info("💡 點擊側邊欄「選擇要顯示的圖表」來篩選要生成的圖表類型")
