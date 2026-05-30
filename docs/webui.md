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

> **安全提醒**：WebUI 沒有認證機制，區域網路內所有裝置均可存取，包含修改 MQTT、API Key、Webhook 等敏感設定。請確認 Pi 只接取可信任的網段，或透過防火牆限制存取。

---

## 設定介面說明

主介面為多頁籤式設定頁面，各頁籤對應不同設定分類：

### 天氣設定

| 欄位 | 說明 |
|------|------|
| **位置（互動地圖）** | 拖曳地圖標記或輸入緯度/經度，設定天氣查詢位置 |
| **API Key** | OpenWeatherMap API Key（輸入後顯示為 `true/false`，不顯示原始值）|
| **單位** | `metric`（°C）或 `imperial`（°F）|
| **更新間隔** | 天氣資料刷新頻率（秒），最小建議 300 秒 |

### MQTT 設定

| 欄位 | 說明 |
|------|------|
| **Broker Host** | MQTT Broker IP 或 hostname |
| **Port** | MQTT 埠號（預設 1883）|
| **Client ID** | 本服務的 MQTT 客戶端識別碼 |

### 顯示器設定

| 欄位 | 說明 |
|------|------|
| **型號** | Waveshare 驅動型號，對應 `lib/waveshare_epd/` 中的驅動檔 |
| **觸發秒** | 每分鐘第幾秒觸發渲染（預設 57，配合 display_lag 使面板在 :00 顯示正確時間）|
| **顯示延遲** | 估計 e-Paper 更新耗時（秒），用於時鐘補償（預設 3）|
| **天氣刷新間隔** | 天氣面板更新頻率（秒）|

### 占用度設定

| 欄位 | 說明 |
|------|------|
| **亮燈權重** | 光線亮度計入占用計分的權重（預設 1.0）|
| **門事件權重** | 近期門事件計入占用計分的權重（預設 1.0）|
| **人臉辨識權重** | 已知人臉辨識計入占用計分的權重（預設 2.0）|
| **閾值** | 總分達到此值判定為 OCCUPIED（預設 2.0）|
| **門事件有效期** | 門事件計分有效時間窗口（秒，預設 300）|
| **人臉辨識有效期** | 人臉事件計分有效時間窗口（秒，預設 600）|

### 語音設定

| 欄位 | 說明 |
|------|------|
| **啟用** | 是否播放音效提醒 |
| **播放指令** | 音效播放器指令（Pi 上使用 `aplay`）|

### 通知設定

| 欄位 | 說明 |
|------|------|
| **Discord Webhook URL** | 安全告警推送目標（留空則停用）⚠️ 服務架構已就緒，告警流程尚未連接，設定後目前不會觸發推送 |

### 一般設定

| 欄位 | 說明 |
|------|------|
| **時區** | 顯示時間與日誌時間戳的時區（如 `Asia/Taipei`）|

---

## REST API 參考

以下為完整的 REST API 端點，可供自動化腳本或 Agent 1 呼叫。

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

回傳 `AgentState` 的 JSON 快照，包含所有感測器讀值、占用狀態、天氣快取、最近 MQTT 事件與 AI 使用量。

**回應範例：**
```json
{
  "temperature": 26.5,
  "humidity": 61.0,
  "light_raw": 680,
  "light_is_bright": true,
  "presence": "OCCUPIED",
  "presence_score": 2.0,
  "weather_current": {"main": "Clear", "temp": 28.0},
  "last_door_event": {"state": "closed", "timestamp": "2026-05-29T10:30:00"},
  "last_face_event": null,
  "last_alert": null,
  "claude_usage_5h": 0.42,
  "claude_usage_week": 0.0,
  "codex_usage_5h": 0.18,
  "codex_usage_week": 0.25,
  "started_at": "2026-05-29T08:00:00"
}
```

> **注意**：使用量欄位為 `0.0–1.0` 浮點數（例如 42% 儲存為 `0.42`）。`claude_usage_week` 目前未從 ai-usage-collector 接收，常態為 `0.0`。

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
    {"ts": "2026-05-29T10:00:00", "score": 2.0, "state": "OCCUPIED", "reason": "..."},
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

回傳目前生效的設定值。**敏感欄位（API Key、Webhook URL）以 `true/false` 表示是否已設定，不回傳原始值。**

**回應範例：**
```json
{
  "mqtt": {"broker_host": "192.168.1.100", "broker_port": 1883, "client_id": "epaper-home-display"},
  "weather": {"api_key_set": true, "lat": 25.05, "lon": 121.53, "units": "metric", "fetch_interval_seconds": 600},
  "display": {"model": "epd7in5_V2", "dashboard_trigger_second": 57, "full_refresh_every": 10},
  "presence": {"light_weight": 1.0, "door_weight": 1.0, "face_weight": 2.0, "threshold": 2.0},
  "discord": {"webhook_set": false},
  "timezone": "Asia/Taipei"
}
```

> **注意**：`weather.api_key` 欄位替換為 `api_key_set`（boolean），`discord.webhook_url` 替換為 `webhook_set`（boolean），原始 secret 值不會回傳。

---

### 讀取 WiFi 資訊

```
GET /settings/wifi
```

**回應範例：**
```json
{
  "ssid": "HomeNetwork",
  "ip": "192.168.1.50",
  "signal": -55
}
```

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

### 更新 MQTT 設定

```
PUT /settings/mqtt
Content-Type: application/json

{
  "broker_host": "192.168.1.100",
  "broker_port": 1883,
  "client_id": "epaper-home-display"
}
```

---

### 更新顯示器設定

```
PUT /settings/display
Content-Type: application/json

{
  "model": "epd7in5_V2",
  "dashboard_trigger_second": 57,
  "full_refresh_every": 10
}
```

| 欄位 | 類型 | 範圍 | 說明 |
|------|------|------|------|
| `dashboard_trigger_second` | int | 0–59 | 每分鐘觸發渲染的秒數；延遲補償自動計算 = 60 − 此值 |
| `full_refresh_every` | int | 1–100 | 每 N 次更新做一次全刷新（清除鬼影）|

---

### 更新占用度設定

```
PUT /settings/presence
Content-Type: application/json

{
  "light_weight": 1.0,
  "door_weight": 1.0,
  "face_weight": 2.0,
  "threshold": 2.0,
  "door_window_seconds": 300,
  "face_window_seconds": 600
}
```

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
  "discord_webhook_url": "https://discord.com/api/webhooks/{id}/{token}"
}
```

留空字串 `""` 可停用 Discord 通知。

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

### 接收 AI 使用量資料

```
POST /ai_usage
Content-Type: application/json

{
  "claude_5h_pct": 42,
  "claude_5h_reset": "18:40",
  "codex_5h_pct": 18,
  "codex_5h_reset": "21:58",
  "codex_weekly_pct": 25,
  "codex_weekly_reset": "17:38 Jun 1"
}
```

此端點由 `tools/ai-usage-collector` 工具自動呼叫，資料會更新 `AgentState` 並記錄至 `ai_usage_logs` 資料表，顯示於 e-Paper 面板底部。

> **注意**：`claude_weekly_pct` 欄位目前不被處理（`claude_usage_week` 狀態維持 0.0）。

**回應：**
```json
{"ok": true, "updated_at": "2026-05-29T14:30:00.123456"}
```

---

## 設定持久化機制

所有 PUT 端點的變更會立即寫入 `config.local.yaml`（原子化覆寫）。`config.local.yaml` 已加入 `.gitignore`，不會隨 `git pull` 被覆蓋。

**優先度**：`config.local.yaml` > `config.yaml` > 程式碼預設值

重啟服務後新設定生效：
```bash
ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'
```

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
