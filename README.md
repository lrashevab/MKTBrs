# 競品輿情分析系統

每次進來看這頁就能快速知道怎麼用。

---

## 一、第一次使用（環境設定）

### 1. 安裝依賴

在專案資料夾開啟終端機，執行：

```bash
python -m pip install -r requirements.txt
playwright install chromium
```

（若終端機找不到 `pip`，一律用 `python -m pip`。）

### 2. 設定 API 金鑰

- 在專案目錄的 **`system.env`** 裡填上你的 **GEMINI_API_KEY**（到 [Google AI Studio](https://aistudio.google.com/app/apikey) 申請）
- 程式會自動讀取 `system.env`，不需改程式碼

---

## 二、平常怎麼用（依需求選一種）

### 方式 A：一次跑完整流程（推薦）

**想做完整市調（需求定義 → 產業掃描 → 競品雷達 → 關鍵字 → Dcard/PTT → 深度分析 → 最終報告）時用這個。**

```bash
python research_orchestrator.py
```

- 依序輸入：調查目的、品牌、產品、產業、目標受眾、預算等級
- 會自動建立 **`campaign_YYYYMMDD_HHMM`** 資料夾，所有產出都在裡面
- 結束後會自動開啟 **FINAL_REPORT.md**

---

### 方式 B：只跑「競品雷達」

**只想快速找競品、產出 competitors.json 與階段一報告時用。**

```bash
python auto_competitor_finder.py
```

- 輸入：品牌名稱、品牌型態、主打產品、產業、目標受眾
- 產出在 **`competitor_reports_YYYYMMDD_HHMM`**（內含 `competitors.json`、`stage1_report_*.md`）

---

### 方式 C：只跑「Dcard 輿情」

**已有關鍵字，只想抓 Dcard 討論與輿情時用。**

```bash
python dcard_scraper.py
```

- 選擇時間範圍（1 個月 / 半年 / 1 年 / 全部）
- 輸入搜尋關鍵字，可選是否用 Gemini 擴充關鍵字
- 產出在 **`reports_YYYYMMDD_HHMM`**（CSV + 輿情 JSON）

---

### 方式 D：只跑「PTT 輿情」

**已有關鍵字，只想搜 PTT 全站討論時用。**

```bash
python ptt_scraper.py
```

- 輸入關鍵字、選擇時間區間（年）
- 看板列表來源：**https://www.ptt.cc/bbs/index.html**（熱門看板首頁）
- 產出在 **`reports_YYYYMMDD_HHMM`**（CSV + 四維度輿情 JSON）

---

### 方式 E：只跑「Threads 搜尋」

**想單獨爬 Threads 關鍵字搜尋結果時用。**

```bash
python threads_scraper.py
```

- 搜尋來源：**https://www.threads.net/search**
- 輸入關鍵字、搜尋天數；產出 CSV／JSON
- 需先安裝：`pip install playwright` 且 `playwright install chromium`

**想讓搜尋更完整（含自己的貼文、較新結果）**：執行時選擇「是否使用已登入帳號」→ 選 **y**。  
第一次會開啟瀏覽器視窗，若出現登入頁請**在該視窗內手動登入**您的 Threads／Facebook 帳號，登入完成後回到終端機按 Enter 繼續。之後同一台電腦再跑會沿用登入狀態，**不需在程式裡填寫帳密**，登入資料只存在本機的 `threads_browser_profile` 資料夾（已列入 .gitignore，不會被提交）。  
若跑完整流程（方式 A）時也要用已登入 Threads，請先在 `threads_scraper.py` 單獨跑一次並登入，再在 **system.env** 加上 `THREADS_USE_LOGGED_IN=1`，之後階段 4 的 Threads 會自動用同一設定檔。

---

### 方式 F：一鍵兩階段（競品 → Dcard/PTT）

**想先找競品，再自動用競品關鍵字跑 Dcard/PTT 時用。**

```bash
python market_orchestrator.py
```

- 建立 **`campaign_YYYYMMDD_HHMM`**
- 跑競品雷達 → 自動帶入關鍵字 → 可選跑 Dcard、PTT
- 所有產出都在同一個 campaign 資料夾

---

## 三、產出放在哪裡

| 執行方式 | 產出資料夾 | 主要檔案 |
|----------|------------|----------|
| **research_orchestrator.py** | `campaign_YYYYMMDD_HHMM` | project_config.json、competitors.json、stage1~6 報告、FINAL_REPORT.md |
| **auto_competitor_finder.py** | `competitor_reports_YYYYMMDD_HHMM` | competitors.json、stage1_report_*.md |
| **dcard_scraper.py** / **ptt_scraper.py** | `reports_YYYYMMDD_HHMM` | dcard_*.csv、ptt_*.csv、*_sentiment_*.json |
| **threads_scraper.py** | 可指定 output_dir 或預設 | threads_*.csv、threads_*.json（來源：threads.net/search） |
| **market_orchestrator.py** | `campaign_YYYYMMDD_HHMM` | 同上，競品 + Dcard + PTT 全在同一夾 |

---

## 四、其他腳本（進階）

| 檔案 | 用途 |
|------|------|
| **main_controller.py** | 用 Gemini 擴充「品牌/競品」關鍵字（鄉民別稱） |
| **keyword_validator.py** | 互動式關鍵字確認與儲存（被 research_orchestrator 呼叫） |
| **ai_analyzer.py** | 讀 Dcard CSV 標題，用 AI 產出行銷分析報告 |
| **report_generator.py** / **visualizer.py** | 報告生成與圖表（可依 campaign 資料夾產出） |

---

## 五、常見問題

- **找不到 `pip`**：改用 `python -m pip install -r requirements.txt`
- **方式 B/C/D/E 一直要我輸入 API 金鑰**：請確認專案目錄下有 **`system.env`**，且內容為 `GEMINI_API_KEY=你的金鑰`。所有入口（含方式 A～F）都會透過 `config.py` 載入 `system.env`，無需在系統環境變數另設。
- **Gemini 404 / 模型不存在**：專案已改為 `gemini-2.5-flash`，可在 `.env` 加 `GEMINI_MODEL=gemini-2.5-flash`
- **Dcard 抓不到內文**：`dcard_scraper.py` 內 `SKIP_CONTENT = True` 時只分析標題與互動數，較穩定；改 `False` 可嘗試抓內文（可能被擋）
- **Linter 報套件找不到**：確認 Cursor 右下角選的是「有裝過 requirements.txt」的那個 Python；或已對選用套件加 `# type: ignore`，不影響執行
- **Threads 沒資料或自己的文沒被收錄**：執行 `threads_scraper.py` 時選「是否使用已登入帳號」→ **y**，第一次在跳出的瀏覽器內手動登入 Threads，之後搜尋會更完整（帳密不寫入程式）

---

**快速記憶**：  
- 要**完整市調一次做完** → `python research_orchestrator.py`  
- 只要**找競品** → `python auto_competitor_finder.py`  
- 只要**Dcard / PTT / Threads** → `python dcard_scraper.py`、`python ptt_scraper.py`、`python threads_scraper.py`
