# WebUI 設定介面

ePaper Home Display 內建 FastAPI Web 設定介面，執行於 Pi 的 `8000` 埠。透過瀏覽器即可調整所有運行參數，無需 SSH 進 Pi 修改設定檔。

---

## 存取方式

```
http://<Pi_IP>:8000/settings
```

例如：`http://192.168.1.50:8000/settings`

Pi 的 IP 可透過路由器管理介面、`arp -a` 或 mDNS hostname 查詢：
```bash
ssh pi@epaper-display.local
# 若 mDNS 可用，也可直接 http://epaper-display.local:8000/settings
```

> **認證機制**：WebUI 受密碼保護。首次存取時會顯示密碼設定頁面，設定後只把 bcrypt 密碼雜湊儲存至 `config.local.yaml`。伺服器端維護單一有效 session slot：閒置 30 分鐘或最長 24 小時後失效，新登入會取代舊 session，登出／改密碼會立即撤銷。所有狀態變更請求都需要 CSRF token。若忘記密碼，可刪除 `config.local.yaml` 中的 `webui.password_hash` 欄位重設。
>
> 管理介面目前預設以 HTTP 提供；HTTP 下 session／CSRF token 仍可能被同網段主動攻擊者攔截與重放，建議限制在信任的隔離 LAN，或另行配置 HTTPS。

---

## 認證

首次連線會顯示密碼設定頁面（`/login?setup=1`），輸入並確認密碼後即可登入。之後每次連線須輸入密碼。`/health` 端點不需認證。

---

## 設定介面說明

主介面為多頁籤式設定頁面，各頁籤對應不同設定分類：

### 天氣設定

| 欄位 | 說明 |
|------|------|
| **位置（離線座標）** | 直接輸入緯度/經度，設定天氣查詢位置；頁面不依賴外部地圖 CDN |
| **API Key** | OpenWeatherMap API Key（輸入後顯示為 `true/false`，不顯示原始值）|
| **單位** | `metric`（°C）或 `imperial`（°F）|
| **更新間隔** | 天氣資料刷新頻率（秒），最小建議 300 秒 |

### 顯示器設定

| 欄位 | 說明 |
|------|------|
| **型號** | Waveshare 驅動型號，對應 `lib/waveshare_epd/` 中的驅動檔。支援：`epd7in3e`（7.3" 七色）、`epd7in5_V2`（7.5" 黑白，支援快速刷新）、`mock`（不寫入硬體）。選擇不存在的型號時，服務啟動時會報錯。|
| **刷新間隔** | Dashboard 每 N 分鐘刷新一次（`dashboard_interval_minutes`，預設 5，必須是 60 的因數）。觸發秒數由型號自動推導（epd7in3e=40, epd7in5_V2=57），不需手動設定。|
| **全刷新間隔** | 每 N 次更新做一次完整刷新（清除鬼影，預設 10）。注意：`epd7in3e` 驅動無快速部分刷新，每次均為完整刷新；`epd7in5_V2` 的非全刷新更新在符合條件時（有上一張畫面可比對、尺寸為面板原生尺寸）會做真正的局部刷新（只送出畫面變化的矩形區域，完全無變化時整次略過寫入），條件不符時 fallback 回原本的快速全畫面刷新，詳見 [docs/architecture.md](architecture.md) 的 e-Paper 更新策略。|

### 占用度設定

| 欄位 | 說明 |
|------|------|
| **光線閾值** | ADC 原始值（0–1023），低於此值視為在場（預設 500）|

占用偵測邏輯為純光線感測：光線 < 閾值 → OCCUPIED，光線 ≥ 閾值 → UNOCCUPIED。

### 語音設定

| 欄位 | 說明 |
|------|------|
| **啟用** | 是否啟用音效功能 |
| **播放指令** | 音效播放器指令（Pi 上使用 `aplay`）|

> **目前狀態**：語音功能為 dormant，沒有自動事件會觸發播放；此頁面的「測試音效」按鈕可手動觸發播放以驗證設定。

### 通知設定

| 欄位 | 說明 |
|------|------|
| **Discord Webhook URL** | 推送通知目標（留空則停用）|
| **裝置上線通知** | 服務啟動時推送（含 WebUI 連結）|
| **時段結束通知** | 桌面工作時段結束時推送摘要 |
| **最短時段時間** | 短於此分鐘數的時段不觸發通知 |
| **每日摘要通知** | 每日固定時間推送昨日統計 |
| **每日摘要時間** | 摘要推送時間（HH:MM 格式，依 `timezone` 設定）|

### 一般設定

| 欄位 | 說明 |
|------|------|
| **時區** | 顯示時間與日誌時間戳的時區（如 `Asia/Taipei`）|

### 環境溫濕度分析

訪問 `/environment` 可查看室內溫濕度的歷史趨勢圖表。支援日（5 分鐘槽平均）、月（每日聚合）、年（每月聚合）三種時間尺度，頁面頂端顯示今日即時讀值與當日極值（min/max/avg）。

---

### AI 使用量設定（僅 YAML）

Claude / Codex 使用量透過服務內建的 OAuth pull 循環自動更新，**WebUI 中無對應設定頁**。相關設定（`claude_usage` / `codex_usage`）只能透過 `config.yaml` 或 `config.local.yaml` 調整。初次授權流程：

```bash
# 在筆電執行（產生 credentials 後 scp 到 Pi）
python tools/claude_auth.py   # 產生 data/claude_creds.json
python tools/codex_auth.py    # 產生 data/codex_creds.json
scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
scp data/codex_creds.json  pi@epaper-display.local:~/epaper-home-display/data/
```

詳見 [docs/configuration.md](configuration.md#ai-使用量)。

---

## REST API 參考

以下為完整的 REST API 端點。以下端點**不需登入 session**：`/health`、`/login`；首次尚未設定管理密碼時，`/wifi`、`/api/wifi/scan`、`/api/wifi/connect` 也可由 AP 設定入口使用，但 WiFi POST 仍需 AP 頁面提供的 per-process CSRF token。管理密碼設定完成後，WiFi 入口改用有效 session 與 session-bound CSRF；其餘端點均需有效 session cookie 與狀態變更用 CSRF token。

### 認證端點

```
GET  /               # 已登入時重新導向至 /settings；未登入的瀏覽器請求（Accept: text/html）導向 /login?next=/；非 HTML 請求（curl 等）回傳 401
GET  /login          # 顯示登入頁面（初次使用時為密碼設定頁）
POST /login          # 提交密碼（form: password, password_confirm, next, csrf）
POST /logout         # 清除 server-side session slot，redirect 至 /login
```

---

### 健康檢查

```
GET /health
```

**回應：**
```json
{"status": "ok"}
```

---

### 讀取目前狀態

```
GET /state
```

回傳 `AgentState` 的**部分欄位** JSON 快照，包含感測器讀值、占用狀態、天氣快取、AI 使用量與 HydraCup 喝水資料。

**回應範例：**
```json
{
  "temperature": 26.5,
  "humidity": 61.0,
  "light_raw": 680,
  "light_is_bright": true,
  "presence": "OCCUPIED",
  "presence_score": 1.0,
  "weather_current": {"main": "Clear", "temp": 28.0},
  "weather_forecast": [...],
  "weather_fetched_at": "2026-05-29T10:00:00",
  "active_reminder": null,
  "display_busy": false,
  "display_page": "dashboard",
  "claude_usage_5h": 0.42,
  "claude_usage_week": 0.0,
  "claude_5h_reset": "18:40",
  "claude_7d_reset": "2d 3h",
  "codex_usage_5h": 0.18,
  "codex_usage_week": 0.25,
  "codex_5h_reset": "21:58",
  "codex_7d_reset": "1d 22h",
  "hydra_current_ml": 1450,
  "hydra_goal_ml": 2000,
  "hydra_pct": 0.725,
  "hydra_updated_at": "2026-05-29T09:55:00",
  "hydra_broker_connected": true,
  "hydra_device_online": true,
  "started_at": "2026-05-29T08:00:00"
}
```

> **注意**：使用量欄位為 `0.0–1.0` 浮點數（例如 42% 儲存為 `0.42`）。重置時間欄位：5h 為 `HH:MM` 格式，7d 為 `"Xd Xh"` 剩餘時間字串（API 未回傳時為 `"--:--"`）。`display_page` 值為 `"dashboard"` 或 `"ap_mode"`。

---

### 讀取日誌

#### 環境日誌（最近 50 筆）

```
GET /logs/env
```

**回應：**
```json
{
  "logs": [
    {"ts": "2026-05-29T10:00:00", "temperature": 26.5, "humidity": 61.0, "light_raw": 680, "light_bright": true},
    ...
  ]
}
```

#### 占用度日誌（最近 50 筆）

```
GET /logs/presence
```

**回應：**
```json
{
  "logs": [
    {"ts": "2026-05-29T10:00:00", "score": 1.0, "state": "OCCUPIED", "reason": "..."},
    ...
  ]
}
```

#### 系統事件日誌（最近 50 筆）

```
GET /logs/events
```

**回應：**
```json
{
  "events": [
    {"ts": "2026-05-29T08:00:00", "level": "info", "module": "main", "message": "Service started"},
    ...
  ]
}
```

---

### 讀取配置

```
GET /settings/config
```

回傳目前生效的設定值。**敏感欄位以遮罩處理，不回傳原始值。**

**回應範例**（混合展示已設定／未設定情境，非預設值；`mqtt` 未設定時預設 `username: ""`、`password_set: false`）：
```json
{
  "weather": {"api_key_set": true, "lat": 25.05, "lon": 121.53, "units": "metric", "fetch_interval_seconds": 600},
  "display": {"model": "epd7in3e", "dashboard_interval_minutes": 5, "full_refresh_every": 10},
  "sensors": {"light": {"bright_threshold": 500}, ...},
  "discord": {"webhook_set": false},
  "mqtt": {"broker_host": "localhost", "broker_port": 1883, "client_id": "epaper-home-display", "username": "epaper-home-display", "password_set": true, "heartbeat_timeout_sec": 180},
  "webui": {"host": "0.0.0.0", "port": 8000},
  "timezone": "Asia/Taipei"
}
```

> **遮罩規則**：`weather.api_key` 替換為 `api_key_set`（boolean）；`discord.webhook_url` 替換為 `webhook_set`（boolean）；`mqtt.password` 替換為 `password_set`（boolean）；`webui.password_hash` 與 `webui.session_secret` 直接移除，不出現於回應中。

---

### 讀取 WiFi 資訊

```
GET /settings/wifi
```

**回應範例：**
```json
{
  "SSID": "HomeNetwork",
  "IP 位址": "192.168.1.50/24",
  "訊號強度": "-55 dBm"
}
```

> 回應鍵為中文顯示用字串，供 WebUI 直接渲染。若無法取得（Pi 未連線或非 Pi 環境），對應值為 `"無法取得"`。

---

### WiFi AP 熱點入口（首次設定免登入；已設定裝置需登入）

以下端點僅在裝置處於 AP 熱點模式時有意義；入口頁不需登入，POST 仍需頁面提供的 per-process CSRF token（設計為供行動裝置的捕獲入口網站使用）。

```
GET  /wifi                  # AP 熱點設定引導頁面（HTML）
GET  /api/wifi/scan         # 掃描周邊 WiFi 網路（AP 模式限定）
POST /api/wifi/connect      # 連接指定 WiFi 網路（AP 模式限定）
```

**`GET /api/wifi/scan` 回應：**
```json
{"networks": [{"ssid": "HomeNetwork", "signal": 75, "security": "WPA2"}, ...]}
```

若裝置不在 AP 模式則回傳 HTTP 503。同一時間只允許一個 nmcli 操作，若操作中則回傳 HTTP 429。Pi Zero 2W 的單 radio 在 AP 模式無法可靠執行 live scan，因此掃描頁優先重新讀取 AP 啟動前由 `wifi_manager.sh` 寫入的 cache；cache 沒有資料時顯示空清單並保留手動輸入 SSID 的路徑。已設定管理密碼的裝置會先要求登入，避免重新進入 AP 模式時繞過管理權限。

**`POST /api/wifi/connect` 請求體：**
```json
{"ssid": "HomeNetwork", "password": "your-password"}
```

`password` 可省略（開放網路）。密碼需至少 8 個字元。

連線流程分兩個階段：
- **Phase 1（同步，含於 HTTP 回應前）**：建立 NetworkManager 連線設定檔；AP 熱點保持啟動，確保客戶端能收到回應。回傳 `{"ok": true, "message": "正在切換網路，AP 熱點即將關閉..."}`。
- **Phase 2（背景任務，回應送出後）**：啟動連線設定檔，AP 熱點關閉；成功後移除 AP 狀態檔，`wifi_monitor` 將在下一個輪詢週期後自動切回儀表板頁面。若啟動失敗，AP 狀態檔保留不刪除，以便使用者重試。

---

> **所有 PUT 端點的回應格式**：成功時回傳 `{"ok": true}`（位置更新額外附上 `lat`/`lon`）；Pydantic 驗證失敗回傳 HTTP 422；持久化失敗回傳 HTTP 500。

### 更新天氣位置

```
PUT /settings/location
Content-Type: application/json

{
  "lat": 25.05,
  "lon": 121.53
}
```

**回應：**
```json
{"ok": true, "lat": 25.05, "lon": 121.53}
```

---

### 更新天氣設定

```
PUT /settings/weather
Content-Type: application/json

{
  "api_key": "your_openweathermap_api_key",
  "units": "metric",
  "fetch_interval_seconds": 600
}
```

所有欄位可選，僅更新提供的欄位。

---

### 更新顯示器設定

```
PUT /settings/display
Content-Type: application/json

{
  "model": "epd7in3e",
  "dashboard_interval_minutes": 5,
  "full_refresh_every": 10
}
```

| 欄位 | 類型 | 範圍 | 說明 |
|------|------|------|------|
| `model` | string | `epd7in3e`, `epd7in5_V2`, `mock` | Waveshare 驅動型號 |
| `dashboard_interval_minutes` | int | 60 的因數（1/2/3/4/5/6/10/12/15/20/30/60）| Dashboard 刷新間隔（分鐘）；觸發秒數由型號自動推導，不可單獨設定 |
| `full_refresh_every` | int | 1–100 | 每 N 次更新做一次全刷新（清除鬼影）|

---

### 更新在場偵測設定

```
PUT /settings/presence
Content-Type: application/json

{
  "bright_threshold": 500
}
```

| 欄位 | 類型 | 範圍 | 說明 |
|------|------|------|------|
| `bright_threshold` | int | 0–1023 | 光線 ADC 值低於此值判定為在場 |

---

### 更新語音設定

```
PUT /settings/voice
Content-Type: application/json

{
  "enabled": true,
  "player": "aplay"
}
```

---

### 更新 Discord 通知

```
PUT /settings/notifications
Content-Type: application/json

{
  "discord_webhook_url": "https://discord.com/api/webhooks/{id}/{token}",
  "notify_device_online": true,
  "notify_session_end": true,
  "session_end_min_minutes": 5,
  "notify_daily_summary": true,
  "daily_summary_time": "23:00"
}
```

所有欄位均可選，僅更新提供的欄位。`discord_webhook_url` 設為空字串 `""` 可停用 Discord 通知。

---

### 更新 HydraCup MQTT 設定

```
PUT /settings/mqtt
Content-Type: application/json

{
  "broker_host": "localhost",
  "broker_port": 1883,
  "client_id": "epaper-home-display",
  "username": "epaper-home-display",
  "password": "your-password",
  "heartbeat_timeout_sec": 180
}
```

| 欄位 | 類型 | 範圍 | 說明 |
|------|------|------|------|
| `broker_host` | string | 非空字串 | Mosquitto broker 位址 |
| `broker_port` | int | 1–65535 | Broker port |
| `client_id` | string | 非空字串 | MQTT client ID |
| `username` | string | 無限制 | Broker 登入帳號；**允許設為空字串**（代表匿名連線嘗試，沿用 `MQTTService` 既有邏輯，API 層不強制非空）|
| `password` | string | 無限制 | Broker 登入密碼；**留空（不提供此欄位）= 不變更既有密碼**，比照 `weather.api_key`／`discord.webhook_url` 的既有模式。與這兩者一致，API 層本身不阻止顯式傳入空字串來清空密碼——保護僅存在於 WebUI 前端（密碼欄位留白就不會加進請求體）|
| `heartbeat_timeout_sec` | int | 10–3600 | 過期判斷秒數 |

所有欄位均可選，僅更新提供的欄位。**儲存後會立即讓執行中的 `MQTTService` 用新設定斷線重連**（不需重啟服務），行為與其他大部分 `PUT /settings/*` 端點「儲存即生效」一致。若即時重連失敗（例如帳密錯誤），端點仍回傳 `{"ok": true}`（設定已正確持久化），連線是否成功由 `GET /state` 的 `hydra_broker_connected` 反映。

---

### 修改密碼

```
PUT /settings/auth
Content-Type: application/json

{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

需提供目前密碼驗證，新密碼長度至少 8 個字元。首次設定密碼請透過登入頁面（`/login`）。

---

### 更新時區

```
PUT /settings/general
Content-Type: application/json

{
  "timezone": "Asia/Taipei"
}
```

有效時區值請參考 [IANA 時區資料庫](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)。

---

---

## 環境溫濕度分析 API

### 目前讀值與今日極值

```
GET /api/env/current
```

**回應：**
```json
{
  "temperature": 26.5,
  "humidity": 61.0,
  "today": {
    "temp_min": 24.1, "temp_max": 28.3, "temp_avg": 26.2,
    "hum_min": 55.0,  "hum_max": 68.0,  "hum_avg": 61.4,
    "sample_count": 48
  }
}
```

`today` 中若當日無資料，各欄位為 `null`，`sample_count` 為 `0`。

> **時區注意**：`/api/env/current` 與 `/api/env/chart` 的「今天」判斷使用 Pi **系統時區**（`datetime.now()`），而非 `config.yaml` 的 `timezone` 設定。若兩者不同，日期邊界可能與 WebUI 顯示時間不一致。建議將 Pi 系統時區設定為與 `config.yaml` 一致：`sudo timedatectl set-timezone Asia/Taipei`。

---

### 環境歷史圖表資料

```
GET /api/env/chart?scale=<day|month|year>[&ref=<ref>]
```

| 參數 | 值 | 說明 |
|------|-----|------|
| `scale` | `day` | 日視圖：5 分鐘槽平均，x 軸為 `HH:MM` |
| `scale` | `month` | 月視圖：每日聚合，x 軸為 `MM-DD` |
| `scale` | `year` | 年視圖：每月聚合，x 軸為月份 `MM` |
| `ref` | `YYYY-MM-DD`（day）| 指定日期（省略則用今天）|
| `ref` | `YYYY-MM`（month）| 指定月份（省略則用本月）|
| `ref` | `YYYY`（year）| 指定年份（省略則用今年）|

`ref` 格式不符時回傳 HTTP 422。

**回應：**
```json
{
  "scale": "day",
  "ref": "2026-06-04",
  "points": [
    {"label": "08:00", "temp": 25.3, "temp_min": 24.8, "temp_max": 25.9,
     "hum": 60.1, "hum_min": 58.5, "hum_max": 61.8}
  ],
  "stats": {
    "temp_min": 24.1, "temp_max": 28.3, "temp_avg": 26.2,
    "hum_min": 55.0,  "hum_max": 68.0,  "hum_avg": 61.4,
    "sample_count": 48
  }
}
```

---

### 有資料的年份清單

```
GET /api/env/years
```

**回應：**
```json
{"years": ["2026", "2025"]}
```

年份降序排列。無資料時回傳 `{"years": []}`。

---

## 圖片管理 API

### 列出圖片

```
GET /api/images
```

**回應：**
```json
{
  "images": [
    {
      "id": "uuid",
      "filename": "photo.jpg",
      "file_size": 102400,
      "created_ts": "2026-05-29T10:00:00",
      "is_current": true
    }
  ]
}
```

### 上傳圖片

```
POST /api/images/upload
Content-Type: multipart/form-data

file: <binary>
```

支援格式由 `images.allowed_formats` 設定決定，預設為 JPEG、PNG、WebP、GIF、BMP（TIFF 需手動加入設定）。大小上限由 `images.max_upload_bytes` 控制（預設 15 MB）。

**回應：**
```json
{"id": "uuid", "orig_w": 3000, "orig_h": 2000}
```

### 預覽裁切效果

```
POST /api/images/preview
Content-Type: application/json

{
  "id": "uuid",
  "crop": {"x": 0, "y": 0, "w": 800, "h": 480},
  "transform": {"rotate": 0, "flip_x": false, "flip_y": false}
}
```

回傳 Floyd-Steinberg dithering 後的 PNG 預覽圖（不寫入 DB）。

### 確認圖片

```
POST /api/images/{id}/confirm
Content-Type: application/json

{
  "crop": {"x": 0, "y": 0, "w": 800, "h": 480},
  "transform": {"rotate": 0, "flip_x": false, "flip_y": false}
}
```

產生 280×448 display PNG（dashboard 圖片區塊尺寸），寫入 DB 並更新輪播狀態（設為目前顯示圖片）。不會強制觸發 e-Paper 立即刷新，新圖片會在下次排定的 dashboard 渲染時顯示。

**回應：**
```json
{"ok": true, "id": "uuid"}
```

### 刪除圖片

```
DELETE /api/images/{id}
```

### 取得圖片檔案

```
GET /api/images/file/{id}        # 取得已確認的 display PNG（280×448，Floyd-Steinberg dithering）
GET /api/images/original/{id}    # 取得原始上傳檔案
```

### 輪播設定

```
GET  /api/images/carousel                    # 讀取輪播設定
PUT  /api/images/carousel                    # 更新輪播設定
PUT  /api/images/carousel/advance            # 手動換圖（僅更新狀態，不強制刷新面板，於下次排定渲染時生效）
```

PUT carousel 請求體：
```json
{
  "enabled": true,
  "interval_minutes": 30,
  "mode": "sequential"
}
```

`mode` 可為 `"sequential"`（順序）或 `"random"`（隨機）。

---

## 桌面工作時段 API

### 今日統計

```
GET /api/desk/stats
```

**回應：**
```json
{
  "presence": "OCCUPIED",
  "light_raw": 680,
  "threshold": 500,
  "today_total_seconds": 14400,
  "today_session_count": 3,
  "current_segment_seconds": 1800,
  "session_start_ts": "2026-05-29T14:00:00",
  "last_change_ts": "2026-05-29T14:00:00"
}
```

### 歷史記錄

```
GET /api/desk/history
```

**回應：**
```json
{
  "timeline_24h": [
    {"id": 1, "start_ts": "2026-05-29T09:00:00", "end_ts": "2026-05-29T12:00:00", "duration_seconds": 10800}
  ],
  "daily_30d": [
    {"date": "2026-05-29", "total_seconds": 28800}
  ]
}
```

### 時段清單

```
GET /api/desk/sessions?limit=20
```

### 年度在席熱力圖

```
GET /api/desk/heatmap?year=2025
```

`year` 省略時使用 Pi 設定時區的目前年份；不可查詢未來年份。回應固定包含該年的 365 或 366 天，跨午夜的時段會按設定時區的午夜切分，進行中的時段會計算到 `as_of`。
前端熱力圖以 8 小時書桌前時間作為滿格強度基準，`reference_seconds` 可供其他客戶端重用同一色階。

`days[].status` 只會是 `future`（尚未到）、`empty`（無記錄）、`recorded`（有記錄）或 `ongoing`（目前仍在席）。`summary` 與頂層的 `total_seconds`、`active_days` 同步，另提供 `session_count` 與 `has_ongoing`。`400` 表示查詢未來年份，`422` 表示 `year` 不在 2000–2100 範圍。

在席時段的新寫入使用帶 UTC offset 的 ISO-8601 時間戳；舊版沒有 offset 的紀錄會先按 Pi 系統時區解讀，再轉換到回應中的 `timezone`，避免設定時區與系統時區不同時錯分日期。

```json
{
  "year": 2025,
  "timezone": "Asia/Taipei",
  "as_of": "2026-07-14T18:20:00+08:00",
  "days": [
    {"date": "2025-01-01", "total_seconds": 28800, "session_count": 1, "status": "recorded"}
  ],
  "total_seconds": 28800,
  "active_days": 1,
  "reference_seconds": 28800,
  "summary": {
    "total_seconds": 28800,
    "active_days": 1,
    "session_count": 1,
    "has_ongoing": false
  }
}
```

---

## 設定持久化機制

所有 PUT 端點的變更會立即寫入 `config.local.yaml`（原子化覆寫）。`config.local.yaml` 已加入 `.gitignore`，不會隨 `git pull` 被覆蓋。

**優先度**：`config.local.yaml` > `config.yaml` > 程式碼預設值

**生效時機**：
- **立即生效（記憶體更新）**：天氣（含地點）、顯示器、在場偵測、語音、Discord 通知、時區、密碼。下次觸發渲染或排程執行時即採用新值，無需重啟。

---

## 使用 curl 測試

```bash
# 健康檢查
curl http://192.168.1.50:8000/health

# 查看目前狀態
curl http://192.168.1.50:8000/state | python3 -m json.tool

# 更新天氣位置到東京
curl -X PUT http://192.168.1.50:8000/settings/location \
  -H "Content-Type: application/json" \
  -d '{"lat": 35.68, "lon": 139.69}'

# 查看環境日誌
curl http://192.168.1.50:8000/logs/env | python3 -m json.tool
```
