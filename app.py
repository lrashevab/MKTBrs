# -*- coding: utf-8 -*-
"""
競品輿情分析系統 — app.py（主入口）
Pip-Boy 復古未來終端機風格  V2.3

啟動：
    .venv/Scripts/streamlit.exe run app.py
"""

import os
import queue
import threading
import time

import streamlit as st

# ─── Page Config（必須是第一個 Streamlit 呼叫）────────────────────────────────
st.set_page_config(
    page_title="INTEL // 競品輿情分析",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS 注入（來自 Design Token 系統）────────────────────────────────────────
from ui.styles import CSS
st.markdown(CSS, unsafe_allow_html=True)

# ─── Session State 預設值 ─────────────────────────────────────────────────────
_STATE_DEFAULTS: dict = {
    "phase":              "form",   # "form" | "running" | "done" | "done_partial" | "error" | "keywords_ready" | "interrupted"
    "scope":              {},
    "log_lines":          [],
    "output_dir":         "",
    "final_file":         "",
    "error_msg":          "",
    "_thread":            None,
    "_log_q":             None,
    "_result_q":          None,
    "_stage4_event":      None,     # threading.Event，Stage 3 後等待確認關鍵字
    "current_tab":        1,
    "selected_keywords":  {},
    "final_keywords":     [],
    "custom_keywords":    [],
    "scan_start_time":    None,
    "_last_toast_phase":  "",
    "_launch_requested":  False,
    "_last_log_activity_ts": None,
    "err_modal_dismissed": False,
    "keywords_confirmed": False,
    "dcard_skipped":      False,    # Bug 2：Dcard 是否被跳過（逾時/封鎖）
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── UI 匯入（延遲至 CSS 注入後）─────────────────────────────────────────────
from ui.layouts import (
    tab_config, tab_scan, tab_process, tab_keywords, tab_intel, tab_export,
    render_header, render_stage_progress, render_status_bar, render_pip_nav,
    render_running_overlay,
)


def _verify_stage_completion(stage_num: int) -> bool:
    """Bug 3：確認 Stage 實際產出預期資料，避免前後台不一致。"""
    if stage_num == 6:
        od = st.session_state.get("output_dir", "")
        ff = st.session_state.get("final_file", "")
        return bool(od and ff and os.path.isfile(os.path.join(od, os.path.basename(ff))))
    return True


def _sync_state_guard() -> None:
    """Bug 3：每次 rerun 執行，確保前台顯示與後台實際狀態一致。"""
    phase = st.session_state.get("phase", "form")
    log_text = "\n".join(st.session_state.get("log_lines", []))
    last_ts = st.session_state.get("_last_log_activity_ts") or 0

    if phase == "done" and not _verify_stage_completion(6):
        st.session_state.phase = "error"
        st.session_state.error_msg = "狀態異常：後台標記完成但報告檔案不存在。"
        st.session_state.log_lines.append("\n[ERR] 狀態異常：後台標記完成但資料不存在")

    if phase == "running" and (time.time() - last_ts) > 600:
        st.session_state.phase = "interrupted"
        st.session_state.error_msg = "執行逾時（10 分鐘無回應），判定為異常中斷。請確認防毒或網路設定後重試。"
        st.session_state.log_lines.append("\n[ERR] 執行逾時（10 分鐘無回應）")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    render_header()

    phase = st.session_state.phase

    # ── 偵測 _launch_requested 旗標，啟動 Pipeline 執行緒 ─────────────────────
    if st.session_state.get("_launch_requested"):
        st.session_state._launch_requested = False
        from pipeline import run_pipeline
        lq: "queue.Queue[str]"  = queue.Queue()
        rq: "queue.Queue[dict]" = queue.Queue()
        ev = threading.Event()
        st.session_state._stage4_event  = ev
        t = threading.Thread(
            target=run_pipeline,
            args=(st.session_state.scope, lq, rq, ev),
            daemon=True,
        )
        t.start()
        st.session_state._log_q         = lq
        st.session_state._result_q     = rq
        st.session_state._thread       = t
        st.session_state.phase         = "running"
        st.session_state.current_tab   = 2
        st.session_state.scan_start_time = time.time()
        st.session_state._last_log_activity_ts = time.time()
        st.session_state.dcard_skipped = False
        phase = "running"

    # ── 偵測執行緒死亡（斷線/程式錯誤）──────────────────────────────────────────
    if phase == "running":
        t = st.session_state.get("_thread")
        if t is not None and not t.is_alive():
            st.session_state.phase = "error"
            st.session_state.error_msg = "Pipeline 執行緒已意外結束（可能為程式錯誤或連線中斷）。請檢查終端機輸出。"
            st.session_state.err_modal_dismissed = False
            phase = "error"

    # ── 狀態同步守衛（Bug 3）：前後台狀態一致性 ───────────────────────────────
    _sync_state_guard()

    # ── 排空 Queue、取得結果（running 或 keywords_ready 時都需輪詢）────────────
    if phase == "running" or phase == "keywords_ready":
        lq = st.session_state._log_q
        rq = st.session_state._result_q
        if lq:
            try:
                while True:
                    line = lq.get_nowait()
                    st.session_state.log_lines.append(line)
                    st.session_state._last_log_activity_ts = time.time()
                    if "專案資料夾：" in line and not st.session_state.output_dir:
                        od = line.split("專案資料夾：")[-1].strip()
                        if os.path.isdir(od):
                            st.session_state.output_dir = od
                    if "Dcard 瀏覽器啟動逾時" in line or "Dcard 分析失敗" in line:
                        st.session_state.dcard_skipped = True
            except queue.Empty:
                pass
        if rq:
            try:
                result = rq.get_nowait()
                if result.get("stage") == "keywords_ready":
                    st.session_state.output_dir = result.get("output_dir", "")
                    st.session_state.phase = "keywords_ready"
                    st.session_state.current_tab = 4
                    phase = "keywords_ready"
                elif "error" in result:
                    st.session_state.error_msg = result["error"]
                    st.session_state.phase = "error"
                    st.session_state.err_modal_dismissed = False
                    phase = "error"
                else:
                    st.session_state.output_dir = result.get("output_dir", "")
                    st.session_state.final_file = result.get("final_file", "")
                    st.session_state.phase = "done"
                    st.session_state.current_tab = 6
                    phase = "done"
            except queue.Empty:
                pass

    # ── Toast 通知（phase 轉換時觸發一次）────────────────────────────────────
    cur_phase = st.session_state.phase
    if cur_phase != st.session_state._last_toast_phase and cur_phase in ("done", "error"):
        msg = "✅ 分析完成！報告已產出" if cur_phase == "done" else f"❌ 分析失敗：{st.session_state.error_msg[:50]}"
        st.toast(msg)
        st.session_state._last_toast_phase = cur_phase

    # ── 計算共用資料 ──────────────────────────────────────────────────────────
    log_text    = "\n".join(st.session_state.log_lines)
    stages_done = sum(f"Stage {n} 完成" in log_text for n in range(1, 7))

    # ── 自動推進頁籤 ──────────────────────────────────────────────────────────
    if phase == "running":
        ct = st.session_state.current_tab
        if ct <= 2 and "Stage 3 完成" in log_text and "Stage 4" not in log_text:
            st.session_state.current_tab = 3
        elif ct <= 3 and ("Stage 4 完成" in log_text or "Stage 5 完成" in log_text):
            st.session_state.current_tab = 4
        elif ct <= 5 and "Stage 6 完成" in log_text:
            st.session_state.current_tab = 6
    elif phase == "keywords_ready":
        st.session_state.current_tab = max(st.session_state.current_tab, 4)
    elif phase == "done":
        st.session_state.current_tab = max(st.session_state.current_tab, 6)
    elif phase in ("error", "interrupted"):
        st.session_state.current_tab = max(st.session_state.current_tab, 2)

    # ── 執行中通知列 / 失敗 Modal（跨頁籤可見，position:fixed）────────────────
    render_running_overlay()

    # ── Stage 時間軸 ──────────────────────────────────────────────────────────
    if phase == "done" or phase == "done_partial":
        current_stage = 7
    elif phase == "form":
        current_stage = 0
    elif phase == "keywords_ready":
        current_stage = 3
    else:
        current_stage = stages_done + 1
    render_stage_progress(current_stage)

    # ── Pip-Boy 導覽列 ────────────────────────────────────────────────────────
    current_tab = st.session_state.current_tab
    new_tab = render_pip_nav(current_tab, phase, log_text)
    if new_tab and new_tab != current_tab:
        st.session_state.current_tab = new_tab
        st.rerun()

    # ── 頁籤內容渲染 ──────────────────────────────────────────────────────────
    ct = st.session_state.current_tab
    if   ct == 1: tab_config()
    elif ct == 2: tab_scan()
    elif ct == 3: tab_process()
    elif ct == 4: tab_keywords()
    elif ct == 5: tab_intel()
    elif ct == 6: tab_export()

    # ── 底部狀態列 ────────────────────────────────────────────────────────────
    render_status_bar(phase, log_text)

    # ── 執行中 / 等待關鍵字確認時自動刷新 ────────────────────────────────────
    if st.session_state.phase == "running":
        time.sleep(3)
        st.rerun()
    if st.session_state.phase == "keywords_ready":
        time.sleep(2)
        st.rerun()


if __name__ == "__main__":
    main()
