# -*- coding: utf-8 -*-
"""
Streamlit 競品輿情分析系統 - 主程式
執行：streamlit run app.py
"""

import streamlit as st
import os
import sys

# 確保可以 import 同目錄下的模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 頁面設定
st.set_page_config(
    page_title="INTEL // 競品輿情分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 深色主題 CSS
st.markdown("""
    <style>
    /* 深色主題 */
    .stApp {
        background-color: #0f0f1a;
    }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
    
    /* 標題 */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    /* 文字 */
    .stMarkdown {
        color: #e0e0e0;
    }
    
    /* 按鈕 */
    .stButton > button {
        background-color: #3f51b5;
        color: white;
        border: none;
        border-radius: 5px;
    }
    .stButton > button:hover {
        background-color: #5c6bc0;
    }
    
    /* 輸入框 */
    .stTextInput > div > div {
        background-color: #1a1a2e;
        color: #ffffff;
    }
    
    /* 表格 */
    div[data-testid="stDataFrame"] {
        background-color: #1a1a2e;
    }
    
    /* 進度條 */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    
    /* 訊息 */
    .stSuccess {
        background-color: #1b5e20;
    }
    .stError {
        background-color: #b71c1c;
    }
    .stWarning {
        background-color: #f57f17;
    }
    
    /* 分隔線 */
    hr {
        border-color: #333333;
    }
    
    /* 導航選項 */
    .nav-item {
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 5px;
        cursor: pointer;
    }
    .nav-item:hover {
        background-color: #2a2a4e;
    }
    .nav-item.active {
        background-color: #3f51b5;
    }
    </style>
""", unsafe_allow_html=True)


def check_api_keys():
    """檢查必要的 API Key"""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    youtube_key = os.getenv("YOUTUBE_API_KEY", "")
    
    return {
        "gemini": bool(gemini_key),
        "youtube": bool(youtube_key),
    }


# Session State 初始化
if "scraped_data" not in st.session_state:
    st.session_state.scraped_data = {}

if "sentiment_results" not in st.session_state:
    st.session_state.sentiment_results = []

if "charts_generated" not in st.session_state:
    st.session_state.charts_generated = {}


# 側邊欄導航
st.sidebar.title("📊 INTEL")
st.sidebar.markdown("---")

# API Key 狀態
api_status = check_api_keys()

st.sidebar.markdown("### 🔑 API 狀態")
if api_status["gemini"]:
    st.sidebar.success("✅ Gemini API 已設定")
else:
    st.sidebar.warning("⚠️ Gemini API 未設定")

if api_status["youtube"]:
    st.sidebar.success("✅ YouTube API 已設定")
else:
    st.sidebar.info("ℹ️ YouTube API 未設定（可略過）")

st.sidebar.markdown("---")

# 導航選項
st.sidebar.markdown("### 📁 功能選單")

page = st.sidebar.radio(
    "選擇功能",
    ["📥 資料收集", "💭 情緒分析", "📈 圖表儀表板", "📤 報告匯出"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ 系統資訊")
st.sidebar.info("""
**INTEL // 競品輿情分析系統**

版本：V3.0
功能：
- 多平台資料爬取
- AI 情緒分析
- 視覺化圖表
- 報告匯出
""")

# 根據選擇顯示對應頁面
if page == "📥 資料收集":
    from pages import data_collection
    data_collection.show()
elif page == "💭 情緒分析":
    from pages import sentiment_analysis
    sentiment_analysis.show()
elif page == "📈 圖表儀表板":
    from pages import dashboard
    dashboard.show()
elif page == "📤 報告匯出":
    from pages import export_report
    export_report.show()
