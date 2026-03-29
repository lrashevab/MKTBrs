# -*- coding: utf-8 -*-
"""
資料收集頁面 - Data Collection
"""

import os
import sys
import time
import pandas as pd
import streamlit as st

# 確保可以 import 同目錄下的模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show():
    st.title("📥 資料收集")
    st.markdown("從多個社群平台收集輿情資料")
    st.markdown("---")
    
    # 檢查 API Key
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        st.error("⚠️ 請先設定 GEMINI_API_KEY 在 system.env")
        st.info("💡 在 system.env 中加入：GEMINI_API_KEY=你的金鑰")
        return
    
    # === 側邊欄設定 ===
    with st.sidebar:
        st.markdown("### ⚙️ 爬蟲設定")
        
        # 平台選擇
        platforms = st.multiselect(
            "選擇平台",
            ["Dcard", "Instagram", "Facebook", "YouTube"],
            default=["Dcard"]
        )
        
        # 關鍵字輸入
        keywords_input = st.text_input(
            "關鍵字（用逗號分隔）",
            placeholder="例如：美食,餐廳,推薦"
        )
        
        # 產業選擇
        industry = st.selectbox(
            "產業類別",
            ["餐飲", "電商", "課程", "旅遊", "美妝保養", "其他"]
        )
        
        # 爬取數量
        max_results = st.slider(
            "爬取數量",
            min_value=10,
            max_value=500,
            value=50,
            step=10
        )
        
        # 時間範圍
        time_range = st.selectbox(
            "時間範圍",
            ["30天內", "90天內", "180天內", "1年內"]
        )
        
        time_map = {"30天內": 30, "90天內": 90, "180天內": 180, "1年內": 365}
        time_range_days = time_map[time_range]
        
        st.markdown("---")
        
        # 執行按鈕
        start_btn = st.button("🚀 開始爬取", type="primary", use_container_width=True)
    
    # === 主畫面 ===
    
    # 解析關鍵字
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    
    if not keywords:
        st.warning("請輸入關鍵字")
        return
    
    if not platforms:
        st.warning("請選擇至少一個平台")
        return
    
    # 顯示設定摘要
    st.info(f"""
    **設定摘要：**
    - 平台：{', '.join(platforms)}
    - 關鍵字：{', '.join(keywords)}
    - 產業：{industry}
    - 數量：最多 {max_results} 筆
    - 時間：{time_range}
    """)
    
    # 執行爬取
    if start_btn:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_results = {}
        
        # 依序爬取各平台
        for i, platform in enumerate(platforms):
            status_text.text(f"正在爬取 {platform}...")
            progress_bar.progress((i / len(platforms)) * 100)
            
            try:
                if platform == "Dcard":
                    from dcard_scraper import run_dcard_scrape
                    results, _ = run_dcard_scrape(
                        keywords=keywords,
                        time_range_days=time_range_days,
                        headless=True
                    )
                    # 轉換為標準格式
                    standardized = []
                    for r in results:
                        standardized.append({
                            "platform": "dcard",
                            "title": r.get("title", ""),
                            "content": r.get("content", ""),
                            "author": r.get("forum", ""),
                            "date": r.get("date", ""),
                            "likes": r.get("likes", 0),
                            "comments": r.get("comments", 0),
                            "url": r.get("link", ""),
                        })
                    all_results["dcard"] = standardized
                    
                elif platform == "Instagram":
                    from instagram_scraper import run_instagram_scrape
                    results, _ = run_instagram_scrape(
                        keywords=keywords,
                        time_range_days=time_range_days,
                        headless=True,
                        max_scroll=max_results // 10
                    )
                    standardized = []
                    for r in results:
                        standardized.append({
                            "platform": "instagram",
                            "title": "",
                            "content": r.get("content", ""),
                            "author": r.get("author", ""),
                            "date": r.get("date_text", ""),
                            "likes": r.get("likes", 0),
                            "comments": r.get("comments", 0),
                            "url": r.get("url", ""),
                        })
                    all_results["instagram"] = standardized
                    
                elif platform == "Facebook":
                    from facebook_scraper import run_facebook_scrape
                    results, _ = run_facebook_scrape(
                        keywords=keywords,
                        time_range_days=time_range_days,
                        headless=True
                    )
                    standardized = []
                    for r in results:
                        standardized.append({
                            "platform": "facebook",
                            "title": "",
                            "content": r.get("content", ""),
                            "author": r.get("author", ""),
                            "date": r.get("date_text", ""),
                            "likes": r.get("likes", 0),
                            "comments": r.get("comments", 0),
                            "url": r.get("url", ""),
                        })
                    all_results["facebook"] = standardized
                    
                elif platform == "YouTube":
                    from youtube_scraper import run_youtube_scrape
                    results, _ = run_youtube_scrape(
                        keywords=keywords,
                        time_range_days=time_range_days,
                        max_videos_per_keyword=max_results
                    )
                    standardized = []
                    for r in results:
                        standardized.append({
                            "platform": "youtube",
                            "title": r.get("title", ""),
                            "content": r.get("description", ""),
                            "author": r.get("channel_title", ""),
                            "date": r.get("published_at", ""),
                            "likes": int(r.get("like_count", 0)),
                            "comments": int(r.get("comment_count", 0)),
                            "url": r.get("video_url", ""),
                        })
                    all_results["youtube"] = standardized
                    
            except Exception as e:
                st.error(f"{platform} 爬取失敗：{str(e)}")
                continue
            
            time.sleep(1)  # 避免太快
        
        # 完成
        progress_bar.progress(100)
        status_text.text("爬取完成！")
        
        # 合併結果
        all_data = []
        for platform, items in all_results.items():
            all_data.extend(items)
        
        if all_data:
            # 儲存到 session state
            st.session_state.scraped_data = all_data
            
            # 顯示結果
            st.success(f"✅ 共爬取 {len(all_data)} 筆資料")
            
            # 轉換為 DataFrame
            df = pd.DataFrame(all_data)
            
            # 顯示預覽
            st.markdown("### 📋 資料預覽")
            st.dataframe(df, use_container_width=True, height=400)
            
            # 平台分布
            if "platform" in df.columns:
                st.markdown("### 📊 平台分布")
                platform_counts = df["platform"].value_counts()
                st.bar_chart(platform_counts)
            
            # 下載按鈕
            st.markdown("### 📥 下載資料")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="⬇️ 下載 CSV",
                    data=csv,
                    file_name="scraped_data.csv",
                    mime="text/csv"
                )
            
            with col2:
                import json
                json_data = json.dumps(all_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ 下載 JSON",
                    data=json_data,
                    file_name="scraped_data.json",
                    mime="application/json"
                )
        else:
            st.warning("沒有爬取到任何資料")
    
    # 顯示已儲存的資料
    elif st.session_state.scraped_data:
        st.success("✅ 已載入之前爬取的資料")
        df = pd.DataFrame(st.session_state.scraped_data)
        st.dataframe(df, use_container_width=True, height=400)
