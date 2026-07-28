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

### 不要用 `claude setup-token` 代替本腳本

`claude setup-token` 會產生一組獨立的長效 token（效期 1 年、無 refresh_token），看起來很適合這種
無人值守的場景，但**它不能用於本功能**：該 token 缺少 `user:profile` scope，呼叫 `/api/oauth/usage`
會回 `403 permission_error: OAuth token does not meet scope requirement user:profile`（2026-07-29 實測）。

`app/services/claude_usage.py` 的 `load_credentials()` 因此明確拒收只有 `access_token` 的憑證——
與其接受後每輪靜默 403、畫面停在 N/A，不如在載入階段就失敗，讓 log 顯示可行動的訊息。

### 部署到 Pi

```bash
scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

Pi 上的 `_claude_usage_loop` 會在下次輪詢時自動載入憑證（不需重啟服務）。Access token 過期時服務會自動
以 refresh_token 刷新，**通常不需要重新執行此腳本**。

### 憑證是共用的：多個用量工具會互相排擠

本腳本產生的憑證是從 `~/.claude/.credentials.json` **複製**出去的。複製後兩邊各自刷新，token 字串會
分岔成不同的兩組，但**限流綁在帳號層級而非 token**，所以 Claude Code CLI 本身、任何讀取同一份憑證檔的
狀態列用量工具、以及 Pi 上的本服務，全部共用同一份 `/api/oauth/usage` 額度（實測兩台機器會同時被 429）。

若 Pi 上的用量長時間顯示 N/A，先盤點還有哪些工具在輪詢這支 API 與各自的頻率，而不是重新產生憑證——
換 token 不會擴大額度。服務本身遇到 429 會依 `Retry-After` 自動退避，詳見
[docs/configuration.md](../docs/configuration.md#claude-使用量)。

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
