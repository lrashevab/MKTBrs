# -*- coding: utf-8 -*-
"""
報告匯出頁面 - Export Report
"""

import os
import sys
import json
import zipfile
import pandas as pd
import streamlit as st
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show():
    st.title("📤 報告匯出")
    st.markdown("將分析結果匯出為報告")
    st.markdown("---")
    
    # 檢查是否有資料
    has_scraped = bool(st.session_state.scraped_data)
    has_analyzed = bool(st.session_state.sentiment_results)
    
    if not has_scraped and not has_analyzed:
        st.warning("尚無資料可供匯出，請先完成「資料收集」與「情緒分析」")
        return
    
    # 側邊欄設定
    with st.sidebar:
        st.markdown("### ⚙️ 匯出設定")
        
        # 選擇要匯出的內容
        st.markdown("#### 選擇資料")
        
        include_scraped = st.checkbox(
            "原始爬取資料",
            value=has_scraped,
            disabled=not has_scraped
        )
        
        include_analyzed = st.checkbox(
            "情緒分析結果",
            value=has_analyzed,
            disabled=not has_analyzed
        )
        
        include_charts = st.checkbox(
            "圖表檔案（PNG）",
            value=False
        )
        
        # 報告標題
        report_title = st.text_input(
            "報告標題",
            value="輿情分析報告"
        )
        
        # 匯出格式
        export_format = st.radio(
            "匯出格式",
            ["ZIP（全部）", "CSV", "JSON"]
        )
        
        generate_btn = st.button("📦 產生報告", type="primary", use_container_width=True)
    
    # 主畫面
    st.markdown("### 📋 匯出預覽")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 原始資料")
        if has_scraped:
            df = pd.DataFrame(st.session_state.scraped_data)
            st.success(f"✅ {len(df)} 筆資料")
            st.dataframe(df.head(5), use_container_width=True)
        else:
            st.info("無原始資料")
    
    with col2:
        st.markdown("#### 分析結果")
        if has_analyzed:
            df = pd.DataFrame(st.session_state.sentiment_results)
            st.success(f"✅ {len(df)} 筆分析")
            
            # 情緒統計
            if "sentiment" in df.columns:
                sentiment_counts = df["sentiment"].value_counts()
                st.write("情緒分布：")
                for sentiment, count in sentiment_counts.items():
                    st.write(f"  - {sentiment}: {count}")
        else:
            st.info("無分析結果")
    
    # 檢查圖表目錄
    charts_dir = "charts"
    chart_files = []
    
    if include_charts and os.path.exists(charts_dir):
        chart_files = [f for f in os.listdir(charts_dir) if f.endswith(".png")]
        st.markdown(f"#### 圖表檔案：{len(chart_files)} 個")
        for cf in chart_files:
            st.write(f"  - {cf}")
    
    # 產生報告
    if generate_btn:
        if not include_scraped and not include_analyzed:
            st.error("請至少選擇一種資料")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 建立輸出目錄
        output_dir = "export_reports"
        os.makedirs(output_dir, exist_ok=True)
        
        # 產生時間戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in report_title if c.isalnum() or c in " _-")
        
        status_text.text("正在產生報告...")
        
        # 收集要匯出的檔案
        files_to_export = []
        
        # 原始資料
        if include_scraped and has_scraped:
            scraped_df = pd.DataFrame(st.session_state.scraped_data)
            csv_path = os.path.join(output_dir, f"原始資料_{timestamp}.csv")
            scraped_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            files_to_export.append(csv_path)
            
            json_path = os.path.join(output_dir, f"原始資料_{timestamp}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(st.session_state.scraped_data, f, ensure_ascii=False, indent=2)
            files_to_export.append(json_path)
        
        progress_bar.progress(30)
        
        # 分析結果
        if include_analyzed and has_analyzed:
            analyzed_df = pd.DataFrame(st.session_state.sentiment_results)
            csv_path = os.path.join(output_dir, f"情緒分析_{timestamp}.csv")
            analyzed_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            files_to_export.append(csv_path)
            
            json_path = os.path.join(output_dir, f"情緒分析_{timestamp}.json")
            analyzed_df.to_json(json_path, orient="records", force_ascii=False, indent=2)
            files_to_export.append(json_path)
        
        progress_bar.progress(60)
        
        # 圖表檔案
        if include_charts and chart_files:
            for cf in chart_files:
                src = os.path.join(charts_dir, cf)
                if os.path.exists(src):
                    files_to_export.append(src)
        
        progress_bar.progress(80)
        
        # 產生 ZIP
        if export_format in ["ZIP（全部）", "ZIP"]:
            zip_path = os.path.join(output_dir, f"{safe_title}_{timestamp}.zip")
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_to_export:
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            
            # 讀取 ZIP 檔案
            with open(zip_path, "rb") as f:
                zip_data = f.read()
            
            st.success("✅ 報告產生完成！")
            
            st.download_button(
                label="⬇️ 下載 ZIP 報告",
                data=zip_data,
                file_name=f"{safe_title}_{timestamp}.zip",
                mime="application/zip"
            )
        
        # CSV 格式
        elif export_format == "CSV":
            if include_scraped:
                csv_path = os.path.join(output_dir, f"{safe_title}_{timestamp}.csv")
                
                if include_analyzed:
                    # 合併兩個資料集
                    merged = pd.concat([
                        scraped_df,
                        analyzed_df
                    ], ignore_index=True)
                    merged.to_csv(csv_path, index=False, encoding="utf-8-sig")
                else:
                    scraped_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                
                with open(csv_path, "rb") as f:
                    csv_data = f.read()
                
                st.success("✅ 報告產生完成！")
                
                st.download_button(
                    label="⬇️ 下載 CSV",
                    data=csv_data,
                    file_name=f"{safe_title}_{timestamp}.csv",
                    mime="text/csv"
                )
        
        # JSON 格式
        elif export_format == "JSON":
            json_output = {
                "report_title": report_title,
                "generated_at": datetime.now().isoformat(),
                "data": {}
            }
            
            if include_scraped:
                json_output["data"]["scraped"] = st.session_state.scraped_data
            
            if include_analyzed:
                json_output["data"]["analyzed"] = st.session_state.sentiment_results.to_dict(orient="records")
            
            json_path = os.path.join(output_dir, f"{safe_title}_{timestamp}.json")
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_output, f, ensure_ascii=False, indent=2)
            
            with open(json_path, "rb") as f:
                json_data = f.read()
            
            st.success("✅ 報告產生完成！")
            
            st.download_button(
                label="⬇️ 下載 JSON",
                data=json_data,
                file_name=f"{safe_title}_{timestamp}.json",
                mime="application/json"
            )
        
        progress_bar.progress(100)
        status_text.text("完成！")
        
        # 顯示匯出檔案清單
        st.markdown("#### 📦 匯出檔案清單")
        for ft in files_to_export:
            st.write(f"  - {os.path.basename(ft)}")
