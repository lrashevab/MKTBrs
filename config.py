# -*- coding: utf-8 -*-
"""
統一配置管理：API 金鑰、系統參數、日誌、速率限制
"""

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore[reportMissingImports]
    _env_path = Path(__file__).parent / "system.env"
    load_dotenv(_env_path)
except ImportError:
    pass  # 如果沒有安裝 python-dotenv，直接使用環境變數


class Config:
    """系統配置類別"""

    # === API 金鑰 ===
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # === 系統路徑 ===
    BASE_DIR = Path(__file__).parent
    OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "reports")
    LOGS_DIR = BASE_DIR / "logs"

    # === 日誌 ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # === 爬蟲設定 ===
    DCARD_MAX_ARTICLES = 300
    DCARD_TOP_COMMENTS = 20       # 每篇 Dcard 文章抓取的熱門留言數
    PTT_MAX_ARTICLES = 300
    PTT_CONTENT_FETCH_LIMIT = 50  # PTT 按互動排序後，前 N 篇完整抓取內文+推文
    REQUEST_TIMEOUT = 30
    RETRY_TIMES = 3

    # === 速率限制（秒），集中管理便於合規與調校 ===
    DCARD_DELAY_MIN = 4.0
    DCARD_DELAY_MAX = 6.0
    PTT_DELAY_BETWEEN_BOARDS = 2.0
    PTT_DELAY_BETWEEN_PAGES = 1.0
    PTT_DELAY_ARTICLE = 0.8
    GOOGLE_NEWS_FETCH_DELAY = 0.4
    GOOGLE_NEWS_FETCH_LIMIT = 50

    # === Gemini 模型設定 ===
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TEMPERATURE = 0.7
    GEMINI_MAX_TOKENS = 8000

    @classmethod
    def setup_logging(cls, log_file_name: str = None):
        """設定根 logger：console + 可選檔案。log_file_name 若為 None 則不寫檔。"""
        level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)
        fmt = logging.Formatter(cls.LOG_FORMAT)
        root = logging.getLogger()
        root.setLevel(level)
        # 避免重複添加 handler
        if root.handlers:
            return
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
        if log_file_name and cls.LOGS_DIR.exists():
            try:
                fh = logging.FileHandler(cls.LOGS_DIR / log_file_name, encoding="utf-8")
                fh.setFormatter(fmt)
                root.addHandler(fh)
            except OSError:
                pass

    @classmethod
    def validate(cls, require_gemini=True):
        """驗證必要配置與合理範圍。非法時僅警告，不中斷啟動。"""
        if require_gemini and not cls.GEMINI_API_KEY:
            print("⚠️ 警告：未設定 GEMINI_API_KEY")
            print("建議：在 system.env 中設定 GEMINI_API_KEY=你的金鑰")
            return False

        cls.LOGS_DIR.mkdir(exist_ok=True)

        # 爬蟲常數合理範圍（僅 warn）
        if not (5 <= cls.REQUEST_TIMEOUT <= 120):
            print("⚠️ 建議：REQUEST_TIMEOUT 介於 5～120 秒較合理")
        if not (1 <= cls.RETRY_TIMES <= 10):
            print("⚠️ 建議：RETRY_TIMES 介於 1～10")
        if cls.DCARD_DELAY_MIN < 1.0 or cls.DCARD_DELAY_MAX > 30.0:
            print("⚠️ 建議：DCARD 延遲介於 1～30 秒，避免過於頻繁請求")
        if cls.PTT_DELAY_BETWEEN_BOARDS < 0.5:
            print("⚠️ 建議：PTT 看板間隔至少 0.5 秒")

        return True


# 只建立資料夾，不強制要求 API 金鑰（由 AI 模組自行驗證）
Config.validate(require_gemini=False)


# ─── App-level UI Constants ───────────────────────────────────────────────────
# 集中定義 app.py 中所有 magic string / magic number，消滅散落的 hardcode。

APP_NAME    = "INTEL // 競品輿情分析系統"
APP_TAGLINE = "COMPETITIVE INTELLIGENCE PLATFORM"
APP_VERSION = "V2.3"

# ── Pipeline Stage 定義 ──────────────────────────────────────────────────────
# 每個 tuple：(stage_num, short_code, label, completion_marker)
# completion_marker 是 log 中用來判斷 Stage 完成的標準字串（唯一來源）
STAGE_DEFS: list = [
    (1, "S1", "產業掃描",  "Stage 1 完成"),
    (2, "S2", "競品雷達",  "Stage 2 完成"),
    (3, "S3", "關鍵字",    "Stage 3 完成"),
    (4, "S4", "社群爬蟲",  "Stage 4 完成"),
    (5, "S5", "AI分析",    "Stage 5 完成"),
    (6, "S6", "報告產出",  "Stage 6 完成"),
]

# 快速查詢：stage_num -> completion_marker
STAGE_MARKERS: dict = {n: marker for n, _, _, marker in STAGE_DEFS}

# 快速查詢：stage_num -> short_code
STAGE_CODES: dict = {n: code for n, code, _, _ in STAGE_DEFS}

# 快速查詢：stage_num -> label
STAGE_LABELS: dict = {n: label for n, _, label, _ in STAGE_DEFS}

# ── Pip-Boy 頁籤定義 ─────────────────────────────────────────────────────────
# (tab_num, display_num, label)
PIP_TABS: list = [
    (1, "01", "CONFIG"),
    (2, "02", "SCAN"),
    (3, "03", "PROCESS"),
    (4, "04", "INTEL"),
    (5, "05", "EXPORT"),
]

# ── 報告模板選項 ─────────────────────────────────────────────────────────────
TEMPLATE_OPTIONS: list = [
    "1 — 執行摘要版",
    "2 — 競品對決版",
    "3 — 深度分析版",
    "4 — 全部產出（推薦）",
]
TEMPLATE_DEFAULT_IDX = 3   # 預設選「4 — 全部產出」

# ── 爬蟲搜尋時間範圍選項（天） ────────────────────────────────────────────────
TIME_RANGE_OPTIONS: list = [30, 60, 90, 180, 270, 365, 730]
TIME_RANGE_DEFAULT = 180

# ── 調查目的選項 ─────────────────────────────────────────────────────────────
PURPOSE_OPTIONS: list = [
    "新品上市前市場評估",
    "競品動態監控",
    "產業趨勢研究",
    "品牌健檢與重新定位",
]
