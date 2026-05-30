# AI Usage Collector

自動採集 **Claude CLI** 和 **Codex CLI** 的配額使用量，推送至 ePaper Home Display 的 WebUI，在 e-Paper 面板上顯示即時的 AI 使用百分比。

---

## 功能

- 並行執行 `claude /usage` 和 `codex /status`，透過 PTY 模擬終端機取得輸出
- 解析 5 小時與週配額使用百分比及重置時間
- POST 至 Pi 的 `/ai_usage` 端點
- 本地快取至 `data/latest.json`

---

## 顯示效果

e-Paper 面板底部會顯示：

```
Claude 5h: 42%  reset 18:40
Codex  5h: 18%  reset 21:58
Codex  Wk: 25%  reset 17:38 Jun 1
```

---

## 系統需求

- Node.js 18+
- Claude CLI（`claude` 指令）
- Codex CLI（`codex` 指令）
- Pi 上的 ePaper Home Display 服務正在運行

---

## 安裝

### Windows（Task Scheduler）

以管理員身分執行 PowerShell：

```powershell
cd tools\ai-usage-collector
.\scripts\setup-windows.ps1
```

腳本會：
1. 安裝 npm 依賴
2. 建立 `.env`（從 `.env.example` 複製）
3. 建立 Windows Task Scheduler 排程任務（定期執行採集）

### macOS / Linux（cron）

```bash
cd tools/ai-usage-collector
bash scripts/setup-mac.sh
```

腳本會：
1. 安裝 npm 依賴
2. 建立 `.env`
3. 新增 cron job（定期執行採集）

---

## 環境變數

複製範本並填入設定：

```bash
cp .env.example .env
```

編輯 `.env`：

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `PI_URL` | 必填 | Pi 的 WebUI 地址，如 `http://192.168.1.xxx:8000` |
| `CODEX_CMD` | `codex` | Codex CLI 指令名稱 |
| `CLAUDE_CMD` | `claude` | Claude CLI 指令名稱 |
| `TUI_STARTUP_MS` | `1500` | CLI 啟動等待時間（毫秒）|
| `TUI_WAIT_MS` | `9000` | 總體超時時間（毫秒）|

---

## 手動執行

### Windows

```powershell
.\scripts\run.ps1
# 或
.\scripts\run.cmd
```

### macOS / Linux

```bash
npx ts-node src/index.ts
```

---

## 卸載

### Windows

```powershell
.\scripts\uninstall-windows.ps1
```

### macOS / Linux

```bash
bash scripts/uninstall-mac.sh
```

---

## 架構

```
src/
├── index.ts          # 主入口：並行採集 → 解析 → 推送
├── tui.ts            # PTY 指令執行（node-pty，跨平台）
├── parse-claude.ts   # 解析 claude /usage 輸出
├── parse-codex.ts    # 解析 codex /status 輸出
├── push.ts           # POST 推送到 Pi
└── debug-raw.ts      # 調試工具（印出原始輸出）

scripts/
├── setup-windows.ps1    # Windows 安裝腳本
├── uninstall-windows.ps1
├── setup-mac.sh         # macOS/Linux 安裝腳本
├── uninstall-mac.sh
├── run.ps1              # Windows 手動執行
└── run.cmd

data/
└── latest.json          # 最新採集結果快取
```

### 執行流程

```
index.ts
  ├── 並行執行 tui.ts（claude /usage）
  │                    tui.ts（codex /status）
  │
  ├── parse-claude.ts → ClaudeUsage { five_hour: { used_pct, reset_text } }
  ├── parse-codex.ts  → CodexStatus { five_hour, weekly }
  │
  ├── 儲存 data/latest.json
  │
  └── push.ts → POST {PI_URL}/ai_usage
```

### PTY 執行機制

`tui.ts` 使用 `node-pty` 建立虛擬終端機（PTY），模擬使用者在終端機中操作 CLI：

1. 啟動 CLI 程序（Windows: `cmd.exe`；macOS/Linux: 直接執行）
2. 等待 `" · Ready · "` 字串出現（或超時 `TUI_STARTUP_MS`）
3. 輸入 slash command（如 `/usage` 或 `/status`）
4. 等待 `TUI_WAIT_MS` 毫秒後 kill 程序，收集完整輸出

### 輸出解析

**Claude `/usage` 輸出範例：**
```
  ● 5-hour usage (42% used, resets 6:40pm (Asia/Taipei))
```
→ `used_pct: 42`, `reset_text: "18:40"`

**Codex `/status` 輸出範例：**
```
  5h limit:  82% left (resets 21:58)
  Weekly limit: 75% left (resets 17:38 on 1 Jun)
```
→ `five_hour.used_pct: 18`, `weekly.used_pct: 25`

---

## 常見問題

### `PI_URL` 連線失敗

確認 Pi 上的 ePaper Home Display 服務正在運行：
```bash
ssh pi@epaper-display.local 'systemctl status epaper-home-display'
```

### CLI 輸出解析失敗

執行 debug 工具查看原始輸出：
```bash
npx ts-node src/debug-raw.ts
```

### `TUI_STARTUP_MS` 超時

若 CLI 啟動較慢，增大 `TUI_STARTUP_MS`（如 `3000`）。

### Windows Task Scheduler 不顯示視窗

正常行為。腳本透過 PowerShell 隱藏視窗執行（`WindowStyle Hidden`）。

---

## 資料格式

推送至 Pi 的 JSON 格式（`POST /ai_usage`）：

```json
{
  "claude_5h_pct": 42,
  "claude_5h_reset": "18:40",
  "codex_5h_pct": 18,
  "codex_5h_reset": "21:58",
  "codex_weekly_pct": 25,
  "codex_weekly_reset": "17:38 Jun 1"
}
```
