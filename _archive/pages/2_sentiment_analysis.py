# -*- coding: utf-8 -*-
"""
情緒分析頁面 - Sentiment Analysis
"""

import os
import sys
import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show():
    st.title("💭 情緒分析")
    st.markdown("使用 AI 分析社群資料的情緒傾向")
    st.markdown("---")
    
    # 產業選擇
    with st.sidebar:
        st.markdown("### ⚙️ 分析設定")
        
        industry = st.selectbox(
            "產業類別",
            ["餐飲", "電商", "課程", "旅遊", "美妝保養", "其他"]
        )
        
        custom_dict_path = st.text_input(
            "自訂詞典路徑（可選）",
            placeholder="custom_dict.json"
        )
        
        analyze_btn = st.button("🔍 開始分析", type="primary", use_container_width=True)
    
    # 資料來源
    st.markdown("### 📂 資料來源")
    
    data_source = st.radio(
        "選擇資料",
        ["使用已爬取的資料", "上傳 CSV 檔案"],
        horizontal=True
    )
    
    df = None
    
    if data_source == "使用已爬取的資料":
        if st.session_state.scraped_data:
            df = pd.DataFrame(st.session_state.scraped_data)
            st.success(f"已載入 {len(df)} 筆資料")
        else:
            st.warning("尚無爬取資料，請先到「資料收集」頁面爬取")
            return
    else:
        uploaded_file = st.file_uploader("上傳 CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.success(f"已載入 {len(df)} 筆資料")
        else:
            return
    
    # 顯示原始資料
    with st.expander("📋 原始資料預覽"):
        st.dataframe(df.head(20), use_container_width=True)
    
    # 執行分析
    if analyze_btn:
        if df is None or len(df) == 0:
            st.error("沒有資料可供分析")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 導入情緒分析模組
        from sentiment_analyzer import analyze_sentiment_v2
        
        results = []
        
        # 分析每一筆資料
        content_col = None
        for col in ["content", "text", "貼文內容", "文章內容"]:
            if col in df.columns:
                content_col = col
                break
        
        if not content_col:
            st.error("找不到內容欄位，請確認 CSV 包含 'content' 或 'text' 欄位")
            return
        
        total = len(df)
        
        for i, row in df.iterrows():
            status_text.text(f"分析中... {i+1}/{total}")
            progress_bar.progress((i + 1) / total * 100)
            
            text = str(row.get(content_col, ""))
            
            if text and text.strip() and text != "nan":
                try:
                    result = analyze_sentiment_v2(
                        text=text,
                        industry=industry if industry != "其他" else None,
                        custom_dict_path=custom_dict_path if custom_dict_path else None
                    )
                except Exception as e:
                    result = {
                        "sentiment": "neutral",
                        "confidence": 0.0,
                        "emotion": None,
                        "positive_keywords": [],
                        "negative_keywords": [],
                        "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                        "language": "unknown"
                    }
            else:
                result = {
                    "sentiment": "neutral",
                    "confidence": 0.0,
                    "emotion": None,
                    "positive_keywords": [],
                    "negative_keywords": [],
                    "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                    "language": "unknown"
                }
            
            results.append({
                "sentiment": result["sentiment"],
                "confidence": result["confidence"],
                "emotion": result["emotion"] or "none",
                "positive_score": result["scores"]["positive"],
                "negative_score": result["scores"]["negative"],
                "neutral_score": result["scores"]["neutral"],
                "positive_keywords": ",".join(result["positive_keywords"]),
                "negative_keywords": ",".join(result["negative_keywords"]),
                "language": result["language"],
            })
        
        # 合併結果
        results_df = pd.concat([df, pd.DataFrame(results)], axis=1)
        
        # 儲存到 session state
        st.session_state.sentiment_results = results_df
        
        progress_bar.progress(100)
        status_text.text("分析完成！")
        
        st.success("✅ 情緒分析完成")
    
    # 顯示分析結果
    if st.session_state.sentiment_results is not None and len(st.session_state.sentiment_results) > 0:
        results_df = st.session_state.sentiment_results
        
        st.markdown("---")
        st.markdown("### 📊 分析結果")
        
        # 情緒分布
        if "sentiment" in results_df.columns:
            st.markdown("#### 情緒分布")
            
            sentiment_counts = results_df["sentiment"].value_counts()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("正面 (Positive)", sentiment_counts.get("positive", 0))
            with col2:
                st.metric("負面 (Negative)", sentiment_counts.get("negative", 0))
            with col3:
                st.metric("中性 (Neutral)", sentiment_counts.get("neutral", 0))
            
            # 圓餅圖
            fig_colors = {"positive": "#4CAF50", "negative": "#F44336", "neutral": "#9E9E9E"}
            pie_data = sentiment_counts.reindex(["positive", "negative", "neutral"], fill_value=0)
            
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 6))
            fig.patch.set_facecolor('#0f0f1a')
            ax.set_facecolor('#0f0f1a')
            
            wedges, texts, autotexts = ax.pie(
                pie_data.values,
                labels=pie_data.index,
                autopct='%1.1f%%',
                colors=[fig_colors.get(x, '#999') for x in pie_data.index],
                textprops={'color': 'white'}
            )
            
            ax.set_title('情緒分布', color='white', fontsize=14)
            st.pyplot(fig)
        
        # 細分情緒分布
        if "emotion" in results_df.columns:
            st.markdown("#### 細分情緒分布")
            
            emotion_counts = results_df["emotion"].value_counts()
            st.bar_chart(emotion_counts)
        
        # 結果表格
        st.markdown("#### 📋 詳細結果")
        
        display_cols = ["sentiment", "confidence", "emotion", "positive_score", "negative_score"]
        available_cols = [c for c in display_cols if c in results_df.columns]
        
        st.dataframe(
            results_df[available_cols],
            use_container_width=True,
            height=400
        )
        
        # 下載按鈕
        st.markdown("### 📥 下載結果")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = results_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="⬇️ 下載 CSV",
                data=csv,
                file_name="sentiment_analysis.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = results_df.to_json(orient="records", force_ascii=False, indent=2)
            st.download_button(
                label="⬇️ 下載 JSON",
                data=json_data,
                file_name="sentiment_analysis.json",
                mime="application/json"
            )
