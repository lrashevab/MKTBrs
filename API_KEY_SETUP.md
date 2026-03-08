# API Key 安全設定說明

## 📋 需要的 API 金鑰

| 金鑰名稱 | 必要性 | 申請網址 | 用途 |
|----------|--------|----------|------|
| `GEMINI_API_KEY` | **必填** | https://aistudio.google.com/app/apikey | AI 分析、關鍵字擴充 |
| `YOUTUBE_API_KEY` | 選填 | https://console.cloud.google.com/ | YouTube 爬蟲（未來功能） |

## 🔧 設定方式

### 方式 1：使用 system.env（推薦）
```bash
# 編輯 system.env 檔案
GEMINI_API_KEY=你的金鑰
YOUTUBE_API_KEY=你的金鑰  # 選填
```

### 方式 2：使用 .env
```bash
# 複製範本
cp .env.example .env

# 編輯 .env 檔案
GEMINI_API_KEY=你的金鑰
```

### 方式 3：環境變數
```bash
# macOS / Linux
export GEMINI_API_KEY=你的金鑰

# Windows CMD
set GEMINI_API_KEY=你的金鑰

# Windows PowerShell
$env:GEMINI_API_KEY="你的金鑰"
```

## ⚠️ 重要提醒

1. **千萬不要提交 .env 或 system.env 到 Git！**
2. `.gitignore` 已設定排除這兩個檔案
3. `.env.example` 是範本檔（不含實際金鑰），可以提交

## ✅ 檢查清單

- [ ] 已填入 GEMINI_API_KEY
- [ ] .env 或 system.env 已設定完成
- [ ] 確認 .gitignore 包含 .env 和 system.env
