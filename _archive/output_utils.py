# -*- coding: utf-8 -*-
"""
報表輸出工具：每次產出建立日期時間資料夾
- 單獨執行：各工具建立自己的 reports_YYYYMMDD_HHMM
- 流程整合（orchestrator）：建立一個 campaign_YYYYMMDD_HHMM，所有階段寫入同一個資料夾
"""

import os
import re
from datetime import datetime


def _safe_print(*args, **kwargs) -> None:
    """print() 的容錯包裝：sys.stdout 失效時（如 Playwright 關閉後）靜默略過。"""
    try:
        # 嘗試導入 Fallout UI 風格
        try:
            from fallout_ui import FalloutUI
            # 如果是狀態訊息，使用 Fallout 風格
            if len(args) == 1 and isinstance(args[0], str):
                msg = args[0]
                if msg.startswith("✅") or "成功" in msg:
                    FalloutUI.print_status('success', msg.replace("✅", "").strip())
                    return
                elif msg.startswith("⚠") or "警告" in msg:
                    FalloutUI.print_status('warning', msg.replace("⚠", "").strip())
                    return
                elif msg.startswith("❌") or "錯誤" in msg:
                    FalloutUI.print_status('error', msg.replace("❌", "").strip())
                    return
        except ImportError:
            pass
        
        print(*args, **kwargs)
    except (ValueError, OSError):
        pass


def _safe_filename(s, max_len: int = 80, default: str = '') -> str:
    """將字串轉成安全的檔名：移除非法字元，截斷至 max_len。
    若結果為空字串，回傳 default。
    """
    result = re.sub(r'[<>:"/\\|?*]', '_', (s or '').strip())[:max_len]
    return result or default


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M")


def get_report_output_dir(base_name="reports"):
    """
    建立並回傳本次報告的輸出資料夾路徑（單獨執行時使用）
    格式：reports_YYYYMMDD_HHMM 或 competitor_reports_YYYYMMDD_HHMM
    """
    ts = _timestamp()
    folder = f"{base_name}_{ts}"
    os.makedirs(folder, exist_ok=True)
    return folder


def get_campaign_output_dir():
    """
    建立並回傳「本次市調專案」的輸出資料夾（流程整合時使用）
    一次執行 = 一個資料夾，第一階段與第二階段皆寫入此夾。
    格式：campaign_YYYYMMDD_HHMM
    """
    ts = _timestamp()
    folder = f"campaign_{ts}"
    os.makedirs(folder, exist_ok=True)
    return folder


def get_report_path(output_dir, filename, extension="csv"):
    """在輸出資料夾內產生完整檔案路徑"""
    if not filename.endswith(f".{extension}"):
        filename = f"{filename}.{extension}"
    return os.path.join(output_dir, filename)
