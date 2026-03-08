# 競品調查產品流程圖 (V1.2)

## 總覽

```
一鍵執行：market_orchestrator.py
   → 建立 campaign_YYYYMMDD_HHMM
   → 第一階段：競品雷達（產出 competitors.json + stage1_report_*.md）
   → 第二階段：Dcard + PTT（產出 dcard_*.csv/json、ptt_*.csv/json）
   → 全部寫入同一個 campaign 資料夾

單獨執行：各工具各自建立資料夾（reports_* 或 competitor_reports_*）
```

---

## 資料夾判定邏輯

| 情境 | 資料夾名稱 | 內容 |
|------|------------|------|
| 執行 **market_orchestrator.py** | `campaign_YYYYMMDD_HHMM` | 第一階段 + 第二階段所有產出（competitors.json、stage1_report、dcard、ptt） |
| 單獨執行 **auto_competitor_finder.py** | `competitor_reports_YYYYMMDD_HHMM` | competitors.json、stage1_report_*.md |
| 單獨執行 **dcard_scraper.py** | `reports_YYYYMMDD_HHMM` | dcard_*.csv、dcard_sentiment_*.json |
| 單獨執行 **ptt_scraper.py** | `reports_YYYYMMDD_HHMM` | ptt_competitor_*.csv、ptt_sentiment_*.json |

**同一專案要放同一夾**：用「一鍵流程」跑一次即可，所有報表會在同一個 `campaign_*` 裡。

---

## 第一階段：雷達掃描 (Market Radar)

**目標**：鎖定戰場與對手（廣度優先）

| 項目 | 說明 |
|------|------|
| 工具 | `auto_competitor_finder.py` |
| 輸入 | 品牌名稱、品牌型態、主打產品、產業、目標受眾 |
| 輸出 | **competitors.json**（供流程整合讀取關鍵字）、**stage1_report_*.md**（第一階段報表）、終端機摘要 |
| 競品標籤範例 | 高價專業版、平價套路版、網紅IP型、企業品牌型、新創小眾型 |

**已優化**：
- 移除 URL 深度驗證（降低 API 消耗與錯誤）
- 競品標籤化 + JSON/報表輸出，支援 `output_dir`（流程整合時寫入 campaign 夾）

---

## 第二階段：深度偵察 (Deep Reconnaissance)

**目標**：挖掘真實痛點（社群討論）

| 項目 | 說明 |
|------|------|
| 工具 | `dcard_scraper.py`、`ptt_scraper.py` |
| 輸入 | 第一階段產出的競品關鍵字（或手動輸入）；流程整合時由 orchestrator 自動帶入 |
| 輸出 | CSV + 四維度輿情 JSON（Dcard / PTT 皆有）；可指定 `output_dir` 寫入同一 campaign |
| 輿情指標 | 市場憤怒指數、跨產業四維度（產品技術觀感 / 情緒焦慮 / 商業消費爭議 / 期待正向） |

**已優化**：
- 每次產出寫入日期時間資料夾（或流程整合時寫入同一 campaign）
- 跨產業通用負評庫 + **產業擴充**（`sentiment_config.py`：餐飲、電商、課程、旅遊、美妝保養）
- PTT 產出四維度輿情 JSON（與 Dcard 格式一致）

---

## 輿情分析說明

### 四維度（跨產業通用）

| 維度 | 情感極性 | 代表詞彙 |
|------|----------|----------|
| 產品技術觀感 | 負面 (覺得假) | 話術、套路、罐頭、背稿、PUA |
| 情緒焦慮 | 中性/焦慮 | 尷尬、自卑、焦慮、緊張、沒自信 |
| 商業消費爭議 | 極度負面 | 割韭菜、盤子、退費、騙、貴 |
| 期待與正向需求 | 正面 (渴望) | 自然、流暢、幽默、有效、專業 |

約會課程圖片為範例，實際詞庫已擴充為**跨產業通用**，可適用課程、電商、餐飲、服務等。

---

## 工具清單與職責

| 工具 | 職責 | 產出 |
|------|------|------|
| `market_orchestrator.py` | 一鍵執行第一階段 + 第二階段，產出寫入同一 campaign | campaign_*/ 內所有檔案 |
| `auto_competitor_finder.py` | 競品掃描、六大維度健檢、競品標籤化 | competitors.json、stage1_report_*.md |
| `dcard_scraper.py` | Dcard 社群聲量、輿情分析、產業詞庫可選 | dcard_*.csv、dcard_sentiment_*.json |
| `ptt_scraper.py` | PTT 全站競品輿情、四維度輿情 | ptt_competitor_*.csv、ptt_sentiment_*.json |
| `sentiment_config.py` | 跨產業負評庫、四維度詞庫、**產業擴充**（餐飲/電商/課程/旅遊/美妝） | 供 dcard/ptt 共用 |
| `output_utils.py` | 日期時間資料夾、campaign 資料夾 | get_report_output_dir、get_campaign_output_dir |

---

## 執行方式

### 方式一：一鍵流程（建議）

```bash
python market_orchestrator.py
```

依序輸入品牌、產業等 → 自動執行第一階段 → 自動帶入關鍵字執行 Dcard / PTT → **所有報表在同一個 campaign_YYYYMMDD_HHMM 資料夾**。

### 方式二：單獨執行

1. `python auto_competitor_finder.py` → 產出至 `competitor_reports_YYYYMMDD_HHMM/`
2. `python dcard_scraper.py` → 產出至 `reports_YYYYMMDD_HHMM/`
3. `python ptt_scraper.py` → 產出至 `reports_YYYYMMDD_HHMM/`

每次執行各自建立新資料夾（以執行當下時間命名）。
