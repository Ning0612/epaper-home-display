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
    gpio_pin: 27    # BCM 腳位號碼，預設 GPIO 27（Pin 13）
                    # 注意：GPIO 17（Pin 11）已被 e-Paper RST 佔用，不可用
    use_mock: false
```

---

## 顯示器

```yaml
display:
  model: "epd7in5_V2"   # Waveshare 型號，對應 lib/waveshare_epd/ 的驅動檔名
  use_mock: false         # true = 不寫入 e-Paper，渲染結果儲存為 debug_frame.png
  dashboard_trigger_second: 57   # 在每分鐘第幾秒觸發渲染，用來補償電子紙刷新延遲
                                  # 延遲補償自動計算 = 60 - 此值（預設 57 → 補償 3 秒）
  full_refresh_every: 10          # 每 N 次更新做一次全刷新（清除鬼影），其餘為快速部分刷新
```

**dashboard_trigger_second 說明**：e-Paper 刷新需要時間，設定在某秒觸發渲染，面板完成刷新時恰好顯示正確分鐘數。延遲補償（秒）= 60 − 觸發秒，由系統自動計算，無需手動設定。

**full_refresh_every 說明**：每 N 次顯示更新執行一次完整刷新（init，清除鬼影），其餘 N-1 次使用快速部分刷新（init_fast）。設定值範圍 1–100，設為 1 代表每次都全刷新。

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

## 圖片輪播

```yaml
images:
  storage_dir: "data/images"       # 圖片存放目錄（含 display PNG 與 tmp 上傳）
  max_count: 50                    # 最多保留已確認圖片數，超過自動刪除最舊的
  max_upload_bytes: 15728640       # 上傳大小上限（bytes，預設 15 MB）
  max_pixels: 100000000            # 圖片像素數上限（預設 1 億像素）
  carousel_enabled: false          # 是否啟用輪播
  carousel_interval_minutes: 30    # 輪播換圖間隔（分鐘）
  carousel_mode: "sequential"      # 換圖模式：sequential（順序）/ random（隨機）
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
    gpio_pin: 27
    use_mock: false

display:
  model: "epd7in5_V2"
  use_mock: false
  dashboard_trigger_second: 57
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
  max_pixels: 100000000
  carousel_enabled: false
  carousel_interval_minutes: 30
  carousel_mode: "sequential"
```
