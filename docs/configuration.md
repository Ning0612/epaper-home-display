# 配置參考

所有設定從 `config.yaml` 讀取，可用 `config.local.yaml` 覆蓋（不影響 `config.yaml`）。

## 優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

> **注意**：目前唯一支援的環境變數覆蓋是 `RPI_MOCK=1`（強制所有硬體使用 mock）。一般設定項目（天氣等）請透過 `config.local.yaml` 或 WebUI 設定，不支援透過環境變數覆蓋。

## 快速建立設定檔

```bash
cp config.example.yaml config.yaml
```

接著編輯 `config.yaml`，至少填入以下必填欄位：
- `weather.api_key`

---

## 天氣

```yaml
weather:
  api_key: "your_openweathermap_api_key"  # 必填：OWM API Key（免費方案即可）
  lat: 25.05    # 緯度（可透過 WebUI 設定頁面直接輸入）
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
    bright_threshold: 500  # 10-bit 閾值（0–1023）；本電路 raw >= 此值是暗光
    unoccupied_after_seconds: 180  # 暗光（raw >= 閾值）持續多久算離開
    occupied_after_seconds: 30     # 亮光（raw < 閾值）持續多久恢復在席
    use_mock: false
```

### 按鈕

```yaml
sensors:
  button:
    gpio_pins: [5, 6, 27, 22]  # B1=GPIO 5（強制 OCCUPIED + 切換 Dashboard）；B2–B4 為硬體保留接腳，目前未綁定任何功能
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
                                  #   mock       = 不寫入硬體，僅記錄 display 呼叫（不存檔）；視覺驗證請用 scripts/preview_render.py
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

**epd7in5_V2 局部刷新說明**：非全刷新的更新在符合條件時（已有上一張成功顯示的畫面、畫面尺寸等於面板原生尺寸），不是單純「較快的全畫面刷新」，而是真正只刷新畫面中有變化的矩形區域（dirty-region，見 `app/display/dirty_region.py`）；跟上一次成功顯示的畫面完全相同時，該次更新會整個略過、不碰面板。條件不符時（例如開機後第一次更新、剛執行過 clear()）會 fallback 回原本的 init_fast 全畫面路徑。這個機制只在 `epd7in5_V2` 有效（`epd7in3e` 沒有對應的驅動 API，行為不受影響），無獨立設定項目，跟隨 `full_refresh_every` 的節奏自動啟用。

---

## 音效

```yaml
voice:
  enabled: true          # false = 停用所有音效（silent mode）
  player: "aplay"        # 播放指令，Pi 使用 "aplay"（ALSA）
  sounds_dir: "assets/sounds"  # 音效檔案目錄
  volume: 80             # 播放音量 0–100（透過 ALSA amixer sset 設定）
  alsa_mixer_control: "PCM"  # ALSA 控制項名稱（常見：PCM / Master）；留空跳過音量設定
  tts_engine: "espeak-ng"    # "espeak-ng"（文字轉語音）| "none"（停用 TTS）
  tts_language: "zh"         # espeak-ng 語音識別碼（zh / zh-TW / en 等）
  tts_speed: 130             # 語速（words per minute），建議 110–150
```

**volume / alsa_mixer_control 說明**：每次播放前自動以 `amixer sset <alsa_mixer_control> <volume>%` 設定音量。不同 Pi 音訊設定的控制項名稱不同，可用 `amixer scontrols` 查詢可用名稱；`alsa_mixer_control` 留空則跳過音量設定（使用系統目前音量）。

**tts_engine 說明**：`espeak-ng` 需在 Pi 安裝套件（`sudo apt install espeak-ng espeak-ng-data`）。`none` 停用 TTS 但仍正常播放 `assets/sounds/` 中的預錄音檔。

> **目前狀態**：語音功能目前為 dormant——沒有任何自動事件會觸發播放，僅能透過 WebUI 設定頁的「測試音效」按鈕手動觸發（呼叫 `POST /settings/voice/test`）。保留此功能是為了未來可能的語音提醒擴充。

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
  daily_summary_time: "23:00"     # 每日摘要時間（HH:MM，依 timezone 設定）
```

通知格式統一為三種訊息：裝置上線文字、時段結束文字，以及包含進度色塊與三欄摘要的每日 Discord embed。Webhook 失敗時仍沿用既有重試佇列。

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

在場偵測使用光敏電路的 ADC 值。此電路的讀值極性與一般直覺相反：
raw < 閾值是實際亮光（在席），raw >= 閾值是實際暗光（離開）。

光線閾值設定位於 `sensors.light.bright_threshold`（可透過 WebUI 設定頁或直接修改 YAML）：

```yaml
sensors:
  light:
    bright_threshold: 500   # ADC 原始值（0–1023）
    unoccupied_after_seconds: 180  # 暗光（raw >= 閾值）持續 180 秒才算離開
    occupied_after_seconds: 30     # 亮光（raw < 閾值）持續 30 秒才恢復在席
```

| 情境 | 結果 |
|------|------|
| 光線讀值 < bright_threshold（實際亮光） | OCCUPIED |
| 光線讀值 ≥ bright_threshold（實際暗光） | UNOCCUPIED |

狀態切換會防抖：暗光持續 `unoccupied_after_seconds` 才切換為 UNOCCUPIED，亮光持續
`occupied_after_seconds` 才切換為 OCCUPIED；候選期間維持原本的穩定狀態。預設分別為 180 秒與 30 秒。

**顯示行為**：人不在時 e-Paper 先清屏，再暫停儀表板更新；偵測到亮光持續達到在席門檻時立即觸發一次更新，後續恢復固定觸發秒節奏。啟動首次顯示與 WiFi 連線切回主畫面時，即使尚未判定在席仍會顯示一次，保留設定入口。

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
`poll_interval_seconds` 可設定範圍 60–1800 秒（1–30 分鐘），也可透過 WebUI `/settings` 頁面「AI 工具用量設定」直接調整（見 [docs/webui.md](webui.md)）。不需要重啟服務；但目前正在進行中的 `asyncio.sleep()` 等待不會被中斷，新值要等這輪等待結束、進入下一輪輪詢週期才會套用。

### Codex 使用量

```yaml
codex_usage:
  creds_path: "data/codex_creds.json"    # OAuth token 儲存路徑（.gitignored）
  poll_interval_seconds: 600              # 每 10 分鐘向 OpenAI WHAM API 拉取一次用量
```

**初次授權**：在筆電執行 `python tools/codex_auth.py`，授權後將 `data/codex_creds.json` scp 到 Pi。
Access token 約 1 小時後過期，服務會自動透過 refresh_token 更新，無需手動介入。
僅在 refresh_token 失效或 Pi log 出現 `re-run tools/codex_auth.py` 警告時，才需重新執行 `codex_auth.py` 並重新 scp。
`poll_interval_seconds` 可設定範圍 60–1800 秒（1–30 分鐘），也可透過 WebUI `/settings` 頁面「AI 工具用量設定」直接調整（見 [docs/webui.md](webui.md)）。不需要重啟服務；但目前正在進行中的 `asyncio.sleep()` 等待不會被中斷，新值要等這輪等待結束、進入下一輪輪詢週期才會套用。

---

## Bambu Lab 3D 印表機

Dashboard 左下角的 Printer 卡片顯示 [Bambu Lab](https://bambulab.com/) 3D 印表機透過雲端 MQTT 推送的列印進度。連線目標固定為 Bambu 雲端 broker（`us.mqtt.bambulab.com:8883`），與 HydraCup 使用的 Pi 上 Mosquitto broker（`mqtt.*` 設定）完全獨立、互不影響。完整協議規格見 [docs/bambu-mqtt-protocol.md](bambu-mqtt-protocol.md)。

```yaml
printer:
  serial: ""                              # 印表機序號，留空則使用 data/bambu_creds.json 裡 tools/bambu_auth.py 自動偵測到的序號
  creds_path: "data/bambu_creds.json"     # Bambu 雲端帳號 token 儲存路徑（.gitignored，不要 commit）
```

**初次授權**：在筆電執行 `python tools/bambu_auth.py`（互動式登入 Bambu Lab 帳號，可能需要信箱驗證碼），完成後將 `data/bambu_creds.json` scp 到 Pi：

```bash
./.venv/Scripts/python.exe tools/bambu_auth.py
scp data/bambu_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

Token 有效期約 3 個月，**沒有實作自動 refresh**。過期後重新執行 `tools/bambu_auth.py` 並重新 scp 即可。

**可透過 WebUI 設定**（`/settings` 頁面「Bambu 印表機設定」區塊，或直接呼叫 `PUT /settings/printer`，見 [docs/webui.md](webui.md)）：只能調整 `serial`，儲存後立即讓執行中的服務用新設定斷線重連，不需重啟。帳號 token/uid 仍必須用 `tools/bambu_auth.py` 更新。

若 `creds_path` 指向的檔案不存在、格式錯誤，或缺少有效的 `access_token`/`uid`/serial，服務會停用此整合、不嘗試連線（記錄 INFO log 說明原因），不影響其餘功能。

---

## HydraCup MQTT

Dashboard 上的 Water 卡片顯示 [esp32-hydracup](https://github.com/Ning0612/esp32-hydracup) 智慧水杯透過 MQTT 推送的喝水資料。完整協議規格見 [docs/hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md)。

**可透過 WebUI 設定**（`/settings` 頁面「HydraCup MQTT 設定」區塊，或直接呼叫 `PUT /settings/mqtt`，見 [docs/webui.md](webui.md)）：儲存後會讓執行中的服務立即用新設定斷線重連，不需重啟。頁面同時顯示目前的 broker 連線狀態與 HydraCup 裝置線上狀態（讀自 `GET /state` 的 `hydra_broker_connected`／`hydra_device_online`）。也可以跳過 WebUI，直接編輯下方的 `config.yaml`：

```yaml
mqtt:
  broker_host: "localhost"          # Mosquitto broker 位址（區網 IP 或 hostname）
  broker_port: 1883
  client_id: "epaper-home-display"
  username: ""                 # 部署上必填：broker 已設定 allow_anonymous false，留空會連線失敗（程式碼本身不強制）
  password: ""                 # 部署上必填：broker 已設定 allow_anonymous false，留空會連線失敗（程式碼本身不強制）
  heartbeat_timeout_sec: 180   # HydraCup 心跳逾時秒數（建議設為裝置端心跳間隔的 3 倍）
```

**broker 帳號建立**（Pi 上手動執行，需 sudo）：

```bash
ssh pi@epaper-display.local
sudo mosquitto_passwd -b /etc/mosquitto/passwd epaper-home-display <password>
sudo systemctl restart mosquitto
```

**heartbeat_timeout_sec 說明**：epaper-display 被動訂閱 `hydracup/status`，不會主動輪詢。若距離上次收到訊息超過此秒數、`hydracup/availability` 回報裝置離線，或 epaper-display 與 MQTT broker 的連線本身中斷，Water 卡片會改用灰階樣式，並隱藏數值（顯示 `--/--ml`），提示資料可能已過期。

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
```

---

## 完整 config.example.yaml

```yaml
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
    unoccupied_after_seconds: 180
    occupied_after_seconds: 30
    use_mock: false
  button:
    gpio_pins: [5, 6, 27, 22]  # B1 dashboard；B2–B4 保留接腳，未綁定功能
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
  volume: 80
  alsa_mixer_control: "PCM"
  tts_engine: "espeak-ng"
  tts_language: "zh"
  tts_speed: 130

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
  # password_hash is managed automatically; session_secret is legacy and ignored

timezone: "Asia/Taipei"

images:
  storage_dir: "data/images"
  max_count: 50
  max_upload_bytes: 15728640
  max_pixels: 25000000
  carousel_enabled: false
  carousel_interval_refreshes: 10   # 每 N 次 dashboard 刷新換圖
  carousel_mode: "sequential"

wifi:
  ap_ssid: "EpaperSetup"
  ap_password: "epaper123"
  connect_timeout: 30
  monitor_interval: 10

claude_usage:
  creds_path: "data/claude_creds.json"
  poll_interval_seconds: 600

mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "epaper-home-display"
  username: ""
  password: ""
  heartbeat_timeout_sec: 180

printer:
  serial: ""
  creds_path: "data/bambu_creds.json"

codex_usage:
  creds_path: "data/codex_creds.json"
  poll_interval_seconds: 600
```

> 上方為精簡範例，逐行註解請參考各章節說明或直接查看 repo 根目錄的 `config.example.yaml`。
