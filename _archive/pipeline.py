# -*- coding: utf-8 -*-
"""
pipeline.py — 後台 Pipeline 執行緒
────────────────────────────────────────────────────────
職責：
  • 包裝整個 6-Stage Pipeline（Gemini AI + 爬蟲 + 報告）
  • 透過 queue.Queue 推送 log 行給 Streamlit 主執行緒
  • 所有互動式 input() 自動回答，不阻塞
  • 不直接操作 st.session_state

公開介面：
  run_pipeline(scope, log_q, result_q) → None
  _StreamlitReportPipeline              # 跳過互動式 ReportPipeline
────────────────────────────────────────────────────────
"""

from __future__ import annotations

import builtins
import json
import os
import queue
import sys
import time
import traceback
from typing import List, Optional

# 專案根目錄，用於寫入 pipeline 錯誤 log
_PIPELINE_LOG_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ERROR_LOG = os.path.join(_PIPELINE_LOG_DIR, "pipeline_errors.log")
_PIPELINE_STAGE_LOG = os.path.join(_PIPELINE_LOG_DIR, "pipeline_stage.log")


# ── 內部：跳過互動式提示的 ReportPipeline ─────────────────────
class _StreamlitReportPipeline:
    """ReportPipeline 子類，略過互動式提示。"""

    def __init__(self, template_choice: str):
        self._template = template_choice

    def generate(self, scope, output_dir, competitors_file, keywords_file,
                 social_results, time_range_days, project_files):
        from orchestrator.report_pipeline import ReportPipeline
        from orchestrator._utils import _safe_print_ctx

        template_choice = self._template

        class _NI(ReportPipeline):
            def _ask_template_choice(self_inner):
                return template_choice
            def _maybe_generate_pdf(self_inner, html_outputs):
                pass

        with _safe_print_ctx():
            return _NI()._run(
                scope, output_dir, competitors_file, keywords_file,
                social_results, time_range_days, project_files,
            )


# ── 內部：從 JSON 取出競品名稱清單 ───────────────────────────
def _load_competitor_names(competitors_file: str) -> List[str]:
    try:
        with open(competitors_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        comp_list = raw.get("competitors", raw) if isinstance(raw, dict) else raw
        if not isinstance(comp_list, list):
            return []
        return [
            c.get("competitor_name", c.get("name", ""))
            for c in comp_list
            if c.get("competitor_name") or c.get("name")
        ]
    except Exception:
        return []


# ── 內部：從 JSON 取出關鍵字清單 ─────────────────────────────
def _load_keywords(keywords_file: str, scope: dict) -> List[str]:
    fallback = [scope.get("brand", ""), scope.get("service", "")]
    try:
        with open(keywords_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        kws: List[str] = []
        kw_obj = data.get("keywords", data)
        if isinstance(kw_obj, dict):
            for kl in kw_obj.values():
                kws.extend(kl if isinstance(kl, list) else [])
        return kws or fallback
    except Exception:
        return fallback


# ── 公開：Pipeline 執行緒主函式 ───────────────────────────────
def run_pipeline(
    scope:    dict,
    log_q:    "queue.Queue[str]",
    result_q: "queue.Queue[dict]",
    start_stage4_event: Optional["threading.Event"] = None,
) -> None:
    """
    在後台執行緒中運行完整 Pipeline（S1~S6）。
    若傳入 start_stage4_event，Stage 3 完成後會推入 keywords_ready 並 wait()，
    待主線程 set() 後才繼續執行 Stage 4～6。
    """
    import io
    import threading as _threading

    # Windows 背景執行緒內若使用 asyncio 子行程，需強制使用 ProactorEventLoop，否則會 NotImplementedError
    if sys.platform == "win32":
        try:
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    def _stage_log(stage_name: str) -> None:
        """寫入目前執行階段到檔案，方便事後排查無 log 的執行緒死亡。"""
        try:
            with open(_PIPELINE_STAGE_LOG, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} — {stage_name}\n")
        except Exception:
            pass

    def _error_file(msg: str) -> None:
        """將錯誤寫入檔案，確保即使 log_q 異常也能留下記錄。"""
        try:
            with open(_PIPELINE_ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} — {msg}\n")
        except Exception:
            pass

    # ── IO 重導向 ──────────────────────────────────────────
    class _QBinaryStream(io.RawIOBase):
        def write(self, b):
            return len(b) if b else 0
        def readable(self): return False
        def writable(self): return True
        def seekable(self): return False

    class _QStream(io.TextIOBase):
        def __init__(self):
            super().__init__()
            self.buffer = io.BufferedWriter(_QBinaryStream())
        def write(self, s: str) -> int:
            s = s.rstrip("\n").rstrip("\r")
            if s:
                log_q.put(s)
            return len(s)
        def flush(self): pass

    _orig_out, _orig_err = sys.stdout, sys.stderr
    sys.stdout = _QStream()
    sys.stderr = _QStream()

    # ── input() 自動回答 ───────────────────────────────────
    _orig_input = builtins.input
    def _auto_input(prompt: str = "") -> str:
        p = prompt.lower()
        answer = "n" if ("(y/n)" in p or "y/n" in p or "y 或 n" in p) else "1"
        log_q.put(f"[--] [自動回應] {prompt.strip()} → {answer}")
        return answer
    builtins.input = _auto_input

    def log(msg: str) -> None:
        try:
            log_q.put(msg)
        except Exception:
            _error_file(f"log_q.put 失敗: {msg[:200]}")

    try:
        _stage_log("Pipeline 啟動")
        # API Key 取得
        try:
            from config import Config
            Config.setup_logging("app.log")
            api_key = Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        except ImportError:
            api_key = os.getenv("GEMINI_API_KEY", "")

        if not api_key:
            log("[ERR] GEMINI_API_KEY 未設定，請在 system.env 填入後重試。")
            result_q.put({"error": "GEMINI_API_KEY not set"})
            return

        from orchestrator import AIAnalyzer, ScraperCoordinator
        from output_utils import get_campaign_output_dir

        # ── Stage 0 ─────────────────────────────────────
        _stage_log("STAGE 0 開始")
        log("[--] ══════════════════════════════════════")
        log("[--]  STAGE 0 — 建立專案資料夾")
        log("[--] ══════════════════════════════════════")
        output_dir = get_campaign_output_dir()
        with open(os.path.join(output_dir, "project_config.json"), "w", encoding="utf-8") as f:
            json.dump(scope, f, ensure_ascii=False, indent=2)
        log(f"[OK]  專案資料夾：{output_dir}")

        ai = AIAnalyzer(api_key=api_key, output_dir=output_dir)

        # ── Stage 1 ─────────────────────────────────────
        _stage_log("STAGE 1 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 1 — 產業掃描 (Gemini)...")
        log("[--] ══════════════════════════════════════")
        ai.scan_industry(industry=scope["industry"], service=scope["service"])
        log("[OK]  Stage 1 完成")

        # ── Stage 2 ─────────────────────────────────────
        _stage_log("STAGE 2 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 2 — 競品雷達 (Gemini)...")
        log("[--] ══════════════════════════════════════")
        manual_list: Optional[List[str]] = (
            scope.get("manual_competitors")
            if scope.get("competitor_source") == "manual" else None
        )
        competitors_file = ai.find_competitors(
            brand=scope["brand"], service=scope["service"],
            industry=scope["industry"], audience=scope.get("audience", ""),
            manual_competitors=manual_list,
        )
        competitor_names = _load_competitor_names(competitors_file)
        log(f"[OK]  Stage 2 完成 — 找到 {len(competitor_names)} 個競品")

        # ── Stage 3 ─────────────────────────────────────
        _stage_log("STAGE 3 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 3 — 關鍵字驗證 (Gemini)...")
        log("[--] ══════════════════════════════════════")
        keywords_file = ai.validate_keywords(
            brand=scope["brand"], competitors=competitor_names,
            industry=scope["industry"], service=scope["service"],
        )
        all_keywords = _load_keywords(keywords_file, scope)
        log(f"[OK]  Stage 3 完成 — {len(all_keywords)} 個關鍵字")

        # ── 等待使用者確認關鍵字後再執行 Stage 4（Bug 1 修復）────────────────
        if start_stage4_event is not None:
            log("[--]  等待使用者在 [04] KEYWORDS 頁籤點擊「確認關鍵字，開始社群爬蟲」...")
            result_q.put({
                "stage": "keywords_ready",
                "output_dir": output_dir,
                "keywords_file": keywords_file,
                "competitors_file": competitors_file,
            })
            start_stage4_event.wait()
            all_keywords = _load_keywords(keywords_file, scope)
            log(f"[--]  已取得確認關鍵字（{len(all_keywords)} 個），開始 Stage 4")

        # ── Stage 4 ─────────────────────────────────────
        _stage_log("STAGE 4 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 4 — 社群聲量爬蟲...")
        enabled_scrapers = scope.get("enabled_scrapers") or None
        _scraper_label = {
            "dcard": "Dcard", "ptt": "PTT", "google_news": "Google News",
            "threads": "Threads", "google_trends": "Google Trends",
            "web_content": "Web Content",
        }
        if enabled_scrapers:
            names = " / ".join(_scraper_label.get(k, k) for k in enabled_scrapers)
        else:
            names = "Dcard / PTT / Google News / Threads / Trends"
        log(f"[--]  已啟用：{names}")
        log("[--] ══════════════════════════════════════")
        time_range_days: int = scope.get("time_range_days", 180)
        time_years: float = time_range_days / 365

        class _NoInputCoordinator(ScraperCoordinator):
            def _ask_time_range(self_inner):
                return time_range_days, time_years

        social_results, _, _ = _NoInputCoordinator().run(
            keywords=all_keywords, kw_label=scope.get("service", ""),
            industry=scope.get("industry"), output_dir=output_dir,
            brand=scope.get("brand", ""), competitor_names=competitor_names,
            enabled_scrapers=enabled_scrapers,
            dcard_headless=scope.get("dcard_headless", True),
        )
        log("[OK]  Stage 4 完成")

        # ── Stage 5 ─────────────────────────────────────
        _stage_log("STAGE 5 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 5 — AI 深度分析 (Gemini)...")
        log("[--] ══════════════════════════════════════")
        analysis_file = ai.deep_analysis(
            scope=scope, competitors_file=competitors_file,
            keywords_file=keywords_file, social_results=social_results,
            time_range_days=time_range_days,
        )
        log("[OK]  Stage 5 完成")

        # ── Stage 6 ─────────────────────────────────────
        _stage_log("STAGE 6 開始")
        log("[--] ══════════════════════════════════════")
        log("[RUN] STAGE 6 — 報告產出...")
        log("[--] ══════════════════════════════════════")
        project_files = {
            "competitors_file": competitors_file,
            "keywords_file":    keywords_file,
            "analysis_report":  analysis_file,
            "social_listening": social_results,
        }
        final_file = _StreamlitReportPipeline(scope.get("template_choice", "4")).generate(
            scope=scope, output_dir=output_dir,
            competitors_file=competitors_file, keywords_file=keywords_file,
            social_results=social_results, time_range_days=time_range_days,
            project_files=project_files,
        )
        log("[OK]  Stage 6 完成")
        log("[--] ══════════════════════════════════════")
        log("[OK]  ██████  全部完成  ██████")
        log("[--] ══════════════════════════════════════")
        result_q.put({"output_dir": output_dir, "final_file": final_file})
        _stage_log("Pipeline 全部完成")

    except (SystemExit, KeyboardInterrupt) as e:
        _stage_log("Pipeline 被中斷 (SystemExit/KeyboardInterrupt)")
        _error_file(f"Pipeline 被中斷: {type(e).__name__} — 可能為 Streamlit 重載、關閉視窗或 Ctrl+C")
        try:
            result_q.put({"error": "Pipeline 被中斷（可能為 Streamlit 重載或程式被關閉）。請勿在執行中儲存檔案或重整頁面。"})
        except Exception:
            pass
        raise
    except BaseException as exc:
        tb = traceback.format_exc()
        err_msg = str(exc)
        _error_file(f"執行失敗: {err_msg}")
        _error_file(tb)
        _stage_log(f"Pipeline 異常結束: {err_msg[:100]}")
        try:
            log(f"[ERR] 執行失敗：{exc}")
            for ln in tb.splitlines():
                log(f"[ERR] {ln}")
        except Exception:
            pass
        try:
            result_q.put({"error": err_msg})
        except Exception as e2:
            _error_file(f"result_q.put 失敗: {e2}")

    finally:
        sys.stdout = _orig_out
        sys.stderr = _orig_err
        builtins.input = _orig_input
