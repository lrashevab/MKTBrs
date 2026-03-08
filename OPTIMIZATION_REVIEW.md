# 競品輿情爬蟲系統 — 三視角審查報告

**審查角度**：設計總監、程式總監、市場總監  
**對標**：Google 產品高水準（可用性、可維護性、數據可信度、商業價值）  
**日期**：2026-03-02

---

## 一、設計總監視角（UX / 視覺 / 資訊架構）

### 已達水準
- **Design System**：HTML 報告採用 CSS 變數、統一色階（ink/surface）、陰影與圓角系統，風格接近 Apple clarity + 麥肯錫深度，專業感足夠。
- **報告分層**：執行摘要 / Battlecard / 深度分析三種模板，對應不同受眾（高層 / 業務 / 策略），資訊架構清晰。
- **互動與匯出**：固定匯出列（PDF、PPTX）、tooltip 說明，降低使用門檻。

### 需調整
| 項目 | 現狀 | 建議 |
|------|------|------|
| **響應式** | KPI/competitor 多為固定欄數（如 4、3 欄） | 小螢幕改為 2/1 欄，加入 `@media (max-width: 768px)` 斷點 |
| **無障礙** | 未見 `aria-*`、焦點管理 | 按鈕/連結補上 `aria-label`，確保鍵盤可操作 |
| **載入與進度** | 僅終端機 print 進度點 | 可選：簡易 Web 進度頁（Flask/FastAPI）或進度條檔案供前端輪詢 |
| **錯誤呈現** | 失敗時多為 console 訊息 | 在報告目錄或 FINAL_REPORT 中列出「本輪未完成項目」與建議動作 |
| **品牌露出** | 報告為通用版型 | 允許 project_config 帶入 logo URL、主色，報告 header 可客製 |

---

## 二、程式總監視角（架構 / 品質 / 維運）

### 已達水準
- **流程編排**：`research_orchestrator` 階段 0～6 分明，依賴單向流動，易理解與擴充。
- **降級策略**：Stage 1 / 5 有備用報告；競品/關鍵字失敗時有 fallback，不中斷整條 pipeline。
- **編碼**：Windows UTF-8 有處理，檔案寫入統一 `encoding='utf-8'` / `utf-8-sig`。
- **爬蟲禮貌**：PTT 有重試、指數退避、看板/頁面間隔；Google 新聞有 `time.sleep(0.4)`；Dcard 有隨機延遲。

### 需調整
| 項目 | 現狀 | 建議 |
|------|------|------|
| **日誌** | 幾乎僅用 `print`，無等級、無檔案 | 使用 `logging`，依 `config.LOG_LEVEL` 輸出至 console + `logs/`，利於除錯與維運 |
| **設定驗證** | `Config.validate` 未在啟動時強制檢查爬蟲常數 | 啟動時檢查 REQUEST_TIMEOUT、RETRY、延遲是否在合理範圍，非法則 warn 或 fail fast |
| **速率限制** | 各爬蟲延遲寫死在程式內 | 延遲常數集中到 `config.py`（如 DCARD_DELAY_MIN/MAX、GOOGLE_NEWS_FETCH_DELAY），便於調校與合規 |
| **錯誤邊界** | 部分 `except Exception` 只 print | 關鍵路徑記錄 `logging.exception`，必要時寫入 `campaign_xxx/errors.log` |
| **型別與介面** | 多處 `Dict`/`List` 未細化 | 關鍵函數補上 TypedDict 或 dataclass，方便重構與靜態檢查 |
| **測試** | 未見單元/整合測試 | 至少為「讀取 project_config + 假資料生成一版報告」寫一個 smoke test |
| **依賴鎖定** | 僅 `requirements.txt` 無版本上限 | 可加 `pip freeze` 或 `constraints.txt` 以便重現環境 |

---

## 三、市場總監視角（數據可信度 / 商業價值 / 合規）

### 已達水準
- **PMM 框架**：深度分析對齊競品維度、SWOT、Battlecard、定位聲明、策略建議，可直接用於提案。
- **多源整合**：Dcard、PTT、Google 新聞、Threads，覆蓋社群與媒體，利於輿情與聲量判斷。
- **輿情結構化**：四維度情緒、憤怒指數、高頻詞，有助解讀「為什麼」而不只「有多少」。

### 需調整
| 項目 | 現狀 | 建議 |
|------|------|------|
| **資料溯源** | Stage 5 僅知道「Dcard/PTT 已完成」 | 將各渠道的摘要（篇數、憤怒指數、Top 關鍵字）注入 prompt，讓 AI 引用具體數字與來源 |
| **時間範圍標示** | 報告內有時未明確寫出搜尋區間 | 所有報告 header 或 meta 顯示「資料區間：YYYY-MM-DD～YYYY-MM-DD」 |
| **取樣說明** | 未說明「前 N 篇」「RSS 筆數上限」 | 在方法論或附錄加一短段：資料來源、時間範圍、取樣方式與限制 |
| **免責與合規** | 無 | 報告 footer 加一句：本報告供內部策略參考，數據來自公開來源與自動化擷取，請依需要驗證關鍵資訊 |
| **競品名單可追溯** | 有 competitors.json | 深度分析中註明「競品來源：AI 掃描 / 手動指定」與時間戳 |

---

## 四、優化項目總覽（本輪已實作 / 建議後續）

### 本輪已實作
1. **config.py**：新增日誌設定、速率限制常數、啟動時設定驗證（延遲與 timeout 合理範圍）。
2. **爬蟲**：統一從 config 讀取 REQUEST_TIMEOUT、延遲常數；關鍵錯誤改為 `logging.exception`。
3. **research_orchestrator**：Stage 5 前彙總各渠道輿情摘要（篇數、憤怒指數、關鍵字），注入 prompt，讓深度分析「有數可引」。
4. **報告**：FINAL_REPORT 與 HTML 可選顯示資料區間；方法論/免責建議寫入本審查文件，供手動加入報告模板。

### 建議後續（本輪已實作）
- ~~響應式與無障礙（CSS + aria）~~ → 已完成：768px/480px 斷點、aria-label、鍵盤可操作。
- ~~單元/整合測試（至少 1 個 smoke test）~~ → 已完成：`tests/test_smoke_report.py`。
- 可選 Web 進度頁或進度檔（未實作）。
- ~~報告模板支援品牌 logo、主色客製~~ → 已完成：`project_config.json` 可選 `logo_url`、`primary_color`（或 `brand_color`）。
- ~~FINAL_REPORT 未完成項目~~ → 已完成：自動列出未完成渠道與建議動作。
- ~~報告資料區間、方法論、免責~~ → 已完成：header 顯示資料區間、footer 方法論與免責聲明；`constraints.txt` 說明依賴鎖定方式。

---

## 五、對標 Google 產品水準的簡要結論

| 維度 | 符合度 | 說明 |
|------|--------|------|
| 使用者體驗 | 中高 | 流程清楚、報告美觀；缺進度可見性與錯誤呈現 |
| 工程品質 | 中 | 架構清楚、有降級；缺日誌、測試、設定驗證 |
| 數據與市場價值 | 中高 | 框架完整、多源整合；需強化溯源與方法論標示 |
| 合規與可解釋性 | 中 | 需補資料區間、取樣說明、免責聲明 |

整體：已具「可交付客戶」的水準；依上述調整後可更接近 Google 級別的**可維運、可追溯、可解釋**標準。
