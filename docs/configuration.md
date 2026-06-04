# 配置參考

所有設定從 `config.yaml` 讀取，可用 `config.local.yaml` 覆蓋（不影響 `config.yaml`）。

## 優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

> **注意**：目前唯一支援的環境變數覆蓋是 `RPI_MOCK=1`（強制所有硬體使用 mock）。一般設定項目（MQTT、天氣等）請透過 `config.local.yaml` 或 WebUI 設定，不支援透過環境變數覆蓋。

## 快速建立設定檔

```bash
cp config.example.yaml config.yaml
```

接著編輯 `config.yaml`，至少填入以下必填欄位：
- `mqtt.broker_host`
- `weather.api_key`

---

## MQTT

```yaml
mqtt:
  broker_host: "192.168.1.100"   # 必填：MQTT Broker IP 或 hostname
  broker_port: 1883               # 可選，預設 1883
  client_id: "epaper-home-display" # 可選，MQTT 客戶端識別碼
  username: ""                    # 可選：Broker 帳號（空字串表示不使用認證）
  password: ""                    # 可選：Broker 密碼
```

---

## 天氣

```yaml
weather:
  api_key: "your_openweathermap_api_key"  # 必填：OWM API Key（免費方案即可）
  lat: 25.05    # 緯度（可透過 WebUI 設定頁面的地圖選取）
  lon: 121.53   # 經度
  units: "metric"   # "metric"（°C）或 "imperial"（°F）
  fetch_interval_seconds: 600   # 天氣更新間隔（秒），預設 10 分鐘
```

取得 API Key：[openweathermap.org](https://openweathermap.org/api) → 免費方案 → My API Keys

---

## 感測器

### DHT22 溫濕度感測器

```yaml
sensors:
  dht22:
    gpio_pin: 4     # BCM 腳位號碼，預設 GPIO 4（Pin 7）
    use_mock: false # true = 使用 mock，回傳固定值（本機開發用）
```

### 光線感測器（MCP3008 ADC）

```yaml
sensors:
  light:
    spi_bus: 0        # SPI bus，固定為 0
    spi_device: 1     # SPI device（CE1），CE0 已被 e-Paper 佔用
    adc_channel: 0    # MCP3008 通道，0–7
    bright_threshold: 500  # 10-bit 閾值（0–1023），超過此值視為「亮」
    use_mock: false
```

### 按鈕

```yaml
sensors:
  button:
    gpio_pins: [5, 6, 27, 22]  # [B1 dashboard, B2 alert-page, B3 trigger-alarm, B4 cancel-alarm]
                                # B1=GPIO 5（強制 OCCUPIED + 切換 Dashboard）
                                # B2=GPIO 6（切換 Alert 頁面）
                                # B3=GPIO 27（重新觸發告警：MQTT publish + 音效）
                                # B4=GPIO 22（取消告警：MQTT publish CANCEL_ALARM）
    use_mock: false
```

---

## 顯示器

```yaml
display:
  model: "epd7in3e"              # Waveshare 型號，對應 lib/waveshare_epd/ 的驅動檔名
                                  # 支援型號：
                                  #   epd7in3e   = 7.3" 七色（黑/白/紅/黃/藍/綠/橙）
                                  #   epd7in5_V2 = 7.5" 黑白，支援快速局部刷新
                                  #   mock       = 不寫入硬體，渲染結果儲存為 debug_frame.png
  use_mock: false
  dashboard_interval_minutes: 5  # Dashboard 刷新間隔（分鐘），必須是 60 的因數（1/2/3/4/5/6/10/12/15/20/30/60）
  full_refresh_every: 10          # 每 N 次更新強制完整刷新（清除鬼影）；epd7in3e 無 init_fast，每次均完整刷新
  # dashboard_trigger_second 不可設定，由 model 自動推導：
  #   epd7in3e   → 40（全刷新 ~20s，在整點前 20s 觸發）
  #   epd7in5_V2 → 57（快速刷新 ~0.3s，在整點前 3s 觸發）
  #   mock       → 57
```

**dashboard_interval_minutes 說明**：Dashboard 每 N 分鐘更新一次（預設 5 分鐘）。系統在每個 N 分鐘邊界前提早觸發渲染，使面板完成刷新時剛好顯示正確時間。觸發秒數由 `model` 自動推導，無需手動設定。

**full_refresh_every 說明**：每 N 次顯示更新強制執行一次完整刷新（init，清除鬼影）。設定值範圍 1–100。注意：`epd7in3e` 驅動無 `init_fast()` 方法，即使設為較大的 N，服務仍會在每次更新時 fallback 至完整刷新（init）。

---

## 音效

```yaml
voice:
  enabled: true          # false = 停用所有音效（silent mode）
  player: "aplay"        # 播放指令，Pi 使用 "aplay"（ALSA）
  sounds_dir: "assets/sounds"  # 音效檔案目錄
```

---

## Discord 通知

```yaml
discord:
  webhook_url: ""   # Discord Webhook URL，留空則停用
                    # 格式：https://discord.com/api/webhooks/{id}/{token}
  notify_device_online: true      # 裝置上線時推送通知（含 WebUI 連結）
  notify_session_end: true        # 桌面工作時段結束時推送摘要
  session_end_min_minutes: 5      # 短於此分鐘數的時段不觸發通知
  notify_daily_summary: true      # 每日固定時間推送昨日統計
  daily_summary_time: "23:00"     # 每日摘要時間（HH:MM，依系統時區）
```

---

## 資料庫

```yaml
storage:
  db_path: "data/epaper-home-display.db"   # SQLite 資料庫路徑（相對於專案根目錄）
```

---

## WebUI

```yaml
webui:
  host: "0.0.0.0"   # 監聽介面，"0.0.0.0" 允許區域網路存取
  port: 8000          # HTTP 埠號
```

訪問 WebUI：`http://<Pi_IP>:8000`

---

## 時區

```yaml
timezone: "Asia/Taipei"   # 用於顯示時間和日誌時間戳
```

有效值請參考 [IANA 時區資料庫](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)。

---

## 在場偵測

在場偵測邏輯為純光源：環境光低於閾值 → OCCUPIED，高於閾值 → UNOCCUPIED。

適用場景：室內書桌/辦公桌，室內燈光使環境光讀值偏低，無人時白天外部自然光讀值偏高。

光線閾值設定位於 `sensors.light.bright_threshold`（可透過 WebUI 設定頁或直接修改 YAML）：

```yaml
sensors:
  light:
    bright_threshold: 500   # ADC 原始值（0–1023），低於此值視為在場
```

| 情境 | 結果 |
|------|------|
| 光線讀值 < bright_threshold | OCCUPIED |
| 光線讀值 ≥ bright_threshold | UNOCCUPIED |

**顯示行為**：人不在時 e-Paper 暫停更新；偵測到剛回家（光線變暗）時立即觸發一次更新，後續恢復固定觸發秒節奏。

---

## 外部攝影機快照

`outdoor_agent` 區段設定外部攝影機的快照整合功能。當收到 MQTT 安全告警時，系統會從此 URL 擷取即時快照並顯示於 e-Paper 告警頁面。

```yaml
outdoor_agent:
  snapshot_url: "http://faceguard.local/snapshot"  # 外部 Agent 快照端點（HTTP GET，回傳 JPEG）
  snapshot_timeout_sec: 2.5  # 擷取超時秒數，網路慢時可適度放寬
  alert_page_enabled: true   # 是否啟用告警頁面（false = 仍顯示一般儀表板）
  alert_page_timeout_sec: 120   # 告警頁面顯示秒數，超時後自動回到儀表板
```

**行為說明**：
- 收到 `home/security/alert` 後立即切換至告警頁面並開始擷取快照
- 快照擷取失敗（逾時、網路錯誤）時靜默降級，仍顯示告警頁面但無圖像
- 超出 `alert_page_timeout_sec` 後自動切回儀表板頁面
- `snapshot_url` 留空或 `alert_page_enabled: false` 時，MQTT callback 仍會短暫設定 `display_page = "alert"`，但 display loop 在每次渲染前執行 `_check_alert_timeout()` 時會立即重置為 `"dashboard"`，實際上不會渲染告警頁面（`/state` 端點可能短暫顯示 `display_page: "alert"`）

---

## WiFi AP 熱點

`wifi` 區段設定 WiFi 狀態監控與 AP 熱點模式。當 Pi 無法連接 WiFi 時（由 `wifi_manager.sh` 管理），服務會偵測到 AP 狀態並在 e-Paper 上顯示連線引導畫面。

```yaml
wifi:
  ap_ssid: "EpaperSetup"   # AP 熱點名稱（由 wifi_manager.sh 建立）
  ap_password: "epaper123" # AP 熱點密碼
  connect_timeout: 30       # WiFi 連線等待超時秒數（供外部腳本參考）
  monitor_interval: 10      # WiFi 狀態輪詢間隔（秒），AP 結束後自動切回儀表板
```

**行為說明**：
- 啟動時讀取 `/tmp/epaper-ap-mode.json` 狀態檔（由 `wifi_manager.sh` 寫入），判斷目前模式
- AP 模式：e-Paper 顯示「掃描 QR code 連接 WiFi」引導頁，並顯示 SSID/密碼
- 每 `monitor_interval` 秒重新偵測一次；使用者透過捕獲入口網站完成設定後自動切回儀表板
- 使用 `nmcli` 檢查 wlan0 連接狀態；開發環境無 nmcli 時假設已連線

> **重要**：`wifi.ap_ssid` / `wifi.ap_password` 是 Python 服務讀取 `/tmp/epaper-ap-mode.json` 失敗時的**顯示備援值**，並非控制 `wifi_manager.sh` 建立熱點所用的實際憑證。  
> 實際熱點帳密由 `scripts/wifi_manager.sh` 的環境變數 `EPAPER_AP_SSID` / `EPAPER_AP_PASS` 決定（預設值同 YAML 預設，均為 `EpaperSetup` / `epaper123`）。  
> 若需修改 AP 帳密，必須同步更新：(1) 本 YAML 設定，(2) `systemd/epaper-wifi-check.service` 的 `Environment=EPAPER_AP_SSID=...` 與 `Environment=EPAPER_AP_PASS=...`，否則顯示值與實際熱點不符。
>
> **權限說明**：`/tmp/epaper-ap-mode.json` 儲存 AP 密碼。`wifi_manager.sh` 使用 `mktemp`（預設 0600，路徑不可猜測）建立暫存檔，寫入 JSON 後先設定權限再 `mv` 至最終路徑；`trap` 確保任何步驟失敗時自動清除暫存檔。若 `pi` 群組存在，強制使用 `chown root:pi && chmod 640`（任一失敗視為硬錯誤並 exit 1，systemd 可偵測）；若 `pi` 群組不存在（自訂使用者名稱的 Pi OS），回退 `chmod 644`（世界可讀）。644 回退為已知安全取捨：在此情境下，`chmod 644` 施加於暫存路徑至 `mv` 之間有極短窗口，但路徑不可猜測；AP 密碼也已顯示於 e-Paper 螢幕上。若部署環境存在非信任本機帳號，建議手動建立 `pi` 群組並將服務使用者加入，以享有 640 保護。

---

## AI 使用量

AI 使用量由服務內建的兩個輪詢循環自動從 API 拉取，無需外部工具。

### Claude 使用量

```yaml
claude_usage:
  creds_path: "data/claude_creds.json"   # OAuth token 儲存路徑（.gitignored）
  poll_interval_seconds: 600              # 每 10 分鐘向 Anthropic API 拉取一次用量
```

**初次授權**：在筆電執行 `python tools/claude_auth.py`，授權後將 `data/claude_creds.json` scp 到 Pi。
支援 Claude Code 原生格式（`claudeAiOauth` 嵌套格式）與標準 snake_case 格式。
Token 過期時自動透過 refresh_token 刷新，不需重新授權。

### Codex 使用量

```yaml
codex_usage:
  creds_path: "data/codex_creds.json"    # OAuth token 儲存路徑（.gitignored）
  poll_interval_seconds: 600              # 每 10 分鐘向 OpenAI WHAM API 拉取一次用量
```

**初次授權**：在筆電執行 `python tools/codex_auth.py`，授權後將 `data/codex_creds.json` scp 到 Pi。
Access token 約 1 小時後過期，服務會自動透過 refresh_token 更新，無需手動介入。
僅在 refresh_token 失效或 Pi log 出現 `re-run tools/codex_auth.py` 警告時，才需重新執行 `codex_auth.py` 並重新 scp。

---

## 圖片輪播

```yaml
images:
  storage_dir: "data/images"           # 圖片存放目錄（含 display PNG 與 tmp 上傳）
  max_count: 50                         # 最多保留已確認圖片數，超過自動刪除最舊的
  max_upload_bytes: 15728640            # 上傳大小上限（bytes，預設 15 MB）
  max_pixels: 25000000                  # 圖片像素數上限（預設 2500 萬像素；Pi Zero 2W 記憶體限制）
  carousel_enabled: false               # 是否啟用輪播
  carousel_interval_refreshes: 10       # 每 N 次 Dashboard 刷新切換一張圖片（不是分鐘數）
  carousel_mode: "sequential"           # 換圖模式：sequential（順序）/ random（隨機）
  # allowed_formats 可選，預設允許 JPEG、PNG、WebP、GIF、BMP
  # 若需加入 TIFF 等格式，明確列出：
  # allowed_formats: ["JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"]
```

---

## config.local.yaml 範例

本機開發時建立 `config.local.yaml`（已加入 `.gitignore`）：

```yaml
# 本機開發覆蓋設定
sensors:
  dht22:
    use_mock: true
  light:
    use_mock: true
  button:
    use_mock: true
display:
  use_mock: true
weather:
  api_key: "my_dev_api_key"
mqtt:
  broker_host: "192.168.1.xxx"
```

---

## 完整 config.example.yaml

```yaml
mqtt:
  broker_host: "192.168.1.100"
  broker_port: 1883
  client_id: "epaper-home-display"
  # username: ""
  # password: ""

weather:
  api_key: "your_openweathermap_api_key"
  lat: 25.05
  lon: 121.53
  units: "metric"
  fetch_interval_seconds: 600

sensors:
  dht22:
    gpio_pin: 4
    use_mock: false
  light:
    spi_bus: 0
    spi_device: 1
    adc_channel: 0
    bright_threshold: 500
    use_mock: false
  button:
    gpio_pins: [5, 6, 27, 22]  # [B1 dashboard, B2 alert-page, B3 trigger-alarm, B4 cancel-alarm]
    use_mock: false

display:
  model: "epd7in3e"
  use_mock: false
  # dashboard_trigger_second 由 model 自動推導，不需設定
  dashboard_interval_minutes: 5  # 必須是 60 的因數（1/2/3/4/5/6/10/12/15/20/30/60）
  full_refresh_every: 10

voice:
  enabled: true
  player: "aplay"
  sounds_dir: "assets/sounds"

discord:
  webhook_url: ""
  notify_device_online: true
  notify_session_end: true
  session_end_min_minutes: 5
  notify_daily_summary: true
  daily_summary_time: "23:00"

storage:
  db_path: "data/epaper-home-display.db"

webui:
  host: "0.0.0.0"
  port: 8000
  # password_hash and session_secret are managed automatically

timezone: "Asia/Taipei"

images:
  storage_dir: "data/images"
  max_count: 50
  max_upload_bytes: 15728640
  max_pixels: 25000000
  carousel_enabled: false
  carousel_interval_refreshes: 10   # 每 N 次 dashboard 刷新換圖
  carousel_mode: "sequential"

outdoor_agent:
  snapshot_url: "http://faceguard.local/snapshot"
  snapshot_timeout_sec: 2.5
  alert_page_enabled: true
  alert_page_timeout_sec: 120

wifi:
  ap_ssid: "EpaperSetup"
  ap_password: "epaper123"
  connect_timeout: 30
  monitor_interval: 10

claude_usage:
  creds_path: "data/claude_creds.json"
  poll_interval_seconds: 600

codex_usage:
  creds_path: "data/codex_creds.json"
  poll_interval_seconds: 600
```
