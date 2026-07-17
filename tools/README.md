# tools/

筆電端一次性執行的工具腳本，用於為 Pi 上的 AI 使用量顯示功能與 Bambu Lab 印表機整合準備憑證。

---

## claude_auth.py — Claude 使用量憑證設定

從 Claude Code 本機憑證提取 OAuth token，存為 Pi 可用的 `data/claude_creds.json`。

### 執行

```bash
python tools/claude_auth.py
```

### 前置條件

需先自行安裝 Claude Code 並完成登入。

### 運作邏輯

| 情境 | 行為 |
|------|------|
| 筆電已安裝 Claude Code | 自動從 `~/.claude/.credentials.json` 提取，無需瀏覽器授權 |
| 未找到 Claude Code 憑證 | 提示自行安裝並登入後重新執行 |
| credentials 格式無效 | 提示確認 Claude Code 已正常登入後重新執行 |

### 輸出

- `data/claude_creds.json`（會嘗試設為僅擁有者可讀寫，POSIX 環境下等同 600 權限；`chmod` 失敗時靜默忽略，不保證一定生效，Windows 筆電上也無法設定 POSIX 權限）
- 內含 `access_token` 與 `refresh_token`

### 部署到 Pi

```bash
scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

Pi 上的 `_claude_usage_loop` 會在下次輪詢時自動載入憑證。Access token 過期時服務會自動以 refresh_token 刷新，**通常不需要重新執行此腳本**。

---

## codex_auth.py — Codex 使用量憑證設定

從 Codex CLI 的本機 auth 檔案提取 OAuth token，存為 Pi 可用的 `data/codex_creds.json`。

### 前置條件

需先自行安裝 Codex CLI 並完成登入（`codex login`）。

### 執行

```bash
python tools/codex_auth.py
```

### 運作邏輯

讀取 `~/.codex/auth.json`，提取 `access_token`、`refresh_token`、`account_id`，並嘗試從 `id_token` JWT payload 解析 `client_id`（供自動刷新使用）。

### 輸出

- `data/codex_creds.json`（會嘗試設為僅擁有者可讀寫，POSIX 環境下等同 600 權限；`chmod` 失敗時靜默忽略，不保證一定生效，Windows 筆電上也無法設定 POSIX 權限）
- 內含 `access_token`、`refresh_token`（若有）、`account_id`、`client_id`（若有）

### 部署到 Pi

```bash
scp data/codex_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

**Token 有效期**：Access token 約 1 小時後過期；若 `refresh_token` 存在，服務會自動刷新。Pi log 出現 `re-run tools/codex_auth.py on laptop` 警告時，才需要重新執行此腳本並重新 scp。

---

## bambu_auth.py — Bambu Lab 印表機憑證設定

互動式登入 Bambu Lab 帳號，取得雲端 MQTT 連線所需的 access token、uid 與印表機序號，存為 Pi 可用的 `data/bambu_creds.json`。

### 執行

```bash
python tools/bambu_auth.py
```

### 運作邏輯

1. 互動輸入 Bambu Lab email 與密碼（密碼用 `getpass`，不明文顯示）。
2. 呼叫登入 API；若回應要求驗證碼（`loginType: verifyCode`），提示到信箱查收驗證碼並輸入。
3. 取得 `access_token` 後，呼叫使用者偏好 API 取得 `uid`。
4. 呼叫裝置綁定 API 取得印表機清單：只有 1 台裝置時自動採用；多台裝置時列出清單供選擇；API 失敗或清單為空時改為手動輸入序號。

### 輸出

- `data/bambu_creds.json`（會嘗試設為僅擁有者可讀寫，POSIX 環境下等同 600 權限；`chmod` 失敗時靜默忽略，不保證一定生效，Windows 筆電上也無法設定 POSIX 權限）
- 內含 `access_token`、`uid`、`serial`

### 部署到 Pi

```bash
scp data/bambu_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

**Token 有效期**：約 3 個月，**本專案未實作自動 refresh**。MQTT 連線失敗且懷疑是憑證過期時，重新執行此腳本並重新 scp 即可。完整協議規格見 [docs/bambu-mqtt-protocol.md](../docs/bambu-mqtt-protocol.md)。

---

## 注意事項

- 三個 credentials 檔案均在 `.gitignore` 中，**不會 commit 到 git**。
- 每次 Pi `git pull` 後憑證不受影響，無需重新 scp（除非 token 失效）。
- Pi 重啟後服務會自動從 `data/` 讀取既有憑證，無需手動介入。
