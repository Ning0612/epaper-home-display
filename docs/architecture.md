# 系統架構

## 開發模型

本專案採用「筆電開發，Pi 部署」的工作流程：

```
筆電  →  編輯程式碼 / 跑單元測試（mock 硬體）/ commit / push
Pi    →  git pull / 跑硬體測試 / 執行主服務
```

Claude Code 在**筆電**上運行。Raspberry Pi 只是部署和硬體測試目標，不預設 Claude Code 已安裝於 Pi 上。

---

## 模組分層

所有程式碼嚴格分為四層，各層之間的依賴方向單向向下：

```
┌─────────────────────────────────────────┐
│  WebUI (app/webui/)                     │  FastAPI / HTTP，監控與設定
├─────────────────────────────────────────┤
│  Business Logic (app/logic/)            │  純函數，無硬體/網路依賴
├─────────────────────────────────────────┤
│  Services (app/services/)               │  MQTT, 天氣 API, 音效, Discord
├─────────────────────────────────────────┤
│  Hardware Drivers (app/sensors/,        │  GPIO, SPI, I2C — 只在此層
│                    app/display/)        │
└─────────────────────────────────────────┘
```

| 層 | 位置 | 規則 |
|----|------|------|
| 硬體驅動 | `app/sensors/`, `app/display/`, `app/services/voice.py` | 所有 GPIO / SPI / I2C 存取只在這裡 |
| 業務邏輯 | `app/logic/` | 不引入任何硬體套件；透過函數參數接收資料 |
| 狀態 | `app/state.py` | 全局可變狀態的唯一來源 |
| WebUI | `app/webui/server.py` | 只做監控與設定，無決策邏輯 |

---

## 目錄結構

```
epaper-home-display/
├── app/
│   ├── main.py              # asyncio 事件循環主入口
│   ├── config.py            # 配置系統（YAML + 環境變數）
│   ├── state.py             # 全局狀態（AgentState dataclass）
│   ├── display/
│   │   ├── epaper.py        # Waveshare 7.5" 驅動包裝
│   │   └── renderer.py      # Pillow 圖像渲染（800×480）
│   ├── logic/
│   │   ├── presence.py      # 占用度計分演算法（純函數）
│   │   ├── alarm_decision.py  # 安全告警決策引擎（純函數）
│   │   └── reminder.py      # 天氣提醒生成（純函數）
│   ├── sensors/
│   │   ├── dht22.py         # DHT22 溫濕度（Real + Mock）
│   │   ├── light_sensor.py  # MCP3008 ADC + 光敏電阻（Real + Mock）
│   │   └── button.py        # GPIO 按鈕（gpiozero）（Real + Mock）
│   ├── services/
│   │   ├── mqtt_client.py   # Paho MQTT Pub/Sub
│   │   ├── weather.py       # OpenWeatherMap API（aiohttp）
│   │   ├── voice.py         # aplay 音效播放
│   │   └── discord.py       # Discord Webhook 通知
│   ├── storage/
│   │   ├── db.py            # SQLite 初始化（WAL 模式）
│   │   └── logs.py          # 非同步事件日誌記錄函數
│   └── webui/
│       └── server.py        # FastAPI 設定頁面 + JSON API
├── tests/                   # pytest 單元測試（mock 硬體）
├── scripts/                 # Pi 硬體獨立測試腳本
├── lib/waveshare_epd/       # Waveshare 驅動（需手動下載）
├── systemd/                 # systemd 服務單元
├── tools/
│   └── ai-usage-collector/  # AI 使用量採集工具（Node.js/TypeScript）
├── docs/                    # 文件
├── assets/                  # 字體、音效、圖片資源
├── data/                    # SQLite 資料庫（git ignored）
├── config.example.yaml      # 配置範本
└── requirements.txt
```

---

## 關鍵資料流

### 感測器 → 狀態 → 顯示

```
DHT22 ──────────────────────────────────────────────────────────┐
光線感測器 ──────────────────────────── app/sensors/ ──► state.py ──► renderer.py ──► epaper.py ──► 硬體
```

### MQTT 入站 → 邏輯 → 出站

```
Agent1 發布：
  home/security/door   ──┐
  home/security/face   ──┼──► mqtt_client.py ──► state.py ──► logic/ ──► 發布：
  home/security/alert  ──┤                                              home/home_state/presence      ⚠️ 計劃中
  home/security/status ──┘                                              home/home_state/alarm_decision ⚠️ 計劃中
```

### 顯示更新觸發條件

```
牆鐘對齊（每分鐘 :57 秒）──────────────────────────────────────┐
MQTT 告警事件（立即） ────────────► display_queue ──► _display_loop ──► renderer ──► epaper
按鈕按下（立即） ─────────────────────────────────────────────┘
```

---

## asyncio 協程架構

`app/main.py` 中以 `asyncio.gather()` 並行執行五個協程：

| 協程 | 觸發週期 | 職責 |
|------|---------|------|
| `_sensor_loop()` | 每 30 秒 | 讀 DHT22 + 光線感測器，更新 state |
| `_presence_loop()` | 每 60 秒 | 查 DB 最近事件 → `compute_presence()` → 提醒 + 告警決策 |
| `_display_loop()` | 牆鐘 :57 秒 | 監聽 display_queue，控制 e-Paper 更新節奏 |
| `_weather_loop()` | 每 600 秒 | 非同步 fetch OpenWeatherMap → 更新 state 快取 |
| `server.serve()` | 持續 | FastAPI WebUI（埠 8000） |

**ThreadPoolExecutor**（3 個工作執行緒）用於阻擋性硬體 I/O（DHT22 感測、SPI 傳輸、e-Paper 驅動）。

**MQTT 執行緒安全**：Paho MQTT 在背景執行緒執行 `loop_start()`，回調透過 `asyncio.run_coroutine_threadsafe()` 安全轉至主 asyncio 循環。

---

## e-Paper 更新策略

電子紙刷新很慢，絕不可阻擋 MQTT 回調或 WebUI 處理程式：

| 更新類型 | 觸發 | 耗時 | 說明 |
|---------|------|------|------|
| 快速更新（`init_fast`）| 牆鐘 :57 | ~1 秒 | 部分刷新，每 10 次中有 9 次 |
| 完整更新（`init`）| 每 10 次快速後 | ~3 秒 | 完整刷新，清除鬼影 |
| 告警立即更新 | MQTT 告警事件 | ~1 秒 | 透過 display_queue |

**牆鐘對齊原理**：在每分鐘第 57 秒觸發渲染，延遲補償自動計算為 `60 - dashboard_trigger_second`（預設 57 → 補償 3 秒），確保面板在整點 :00 顯示正確的分鐘數。

---

## 占用度計分系統

`app/logic/presence.py` 中的純函數 `compute_presence()`：

```
score = 0

if light_is_bright:                              score += light_weight  (預設 1.0)
if 最近 5 分鐘有門事件:                           score += door_weight   (預設 1.0)
if 最近 10 分鐘有已知人臉:                        score += face_weight   (預設 2.0)

result = "OCCUPIED"   if score >= threshold (2.0)
       = "UNOCCUPIED" otherwise
       
button_override = True  →  強制 "OCCUPIED"，不計算分數
```

---

## 安全告警決策

`app/logic/alarm_decision.py` 中的純函數 `compute_alarm_decision()`：

```
if presence ∈ {UNOCCUPIED, UNKNOWN} AND 最近無已知人臉  →  ALARM
elif presence == OCCUPIED AND 有已知人臉                →  IGNORE
else                                                    →  INVESTIGATE
```

---

## 天氣提醒生成

`app/logic/reminder.py` 判斷條件：

| 條件 | 提醒內容 |
|------|---------|
| 未來 8 小時有雨（OWM 代碼 200-532）| 帶傘 |
| 溫度下降 > 5°C | 帶夾克 |
| 室內濕度 > 80% | 開除濕機 |
| 室內溫度 > 30°C | 開冷氣 |

---

## 全局狀態（AgentState）

`app/state.py` 定義的全局單例 `state = AgentState()`，被所有模組引用：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `temperature` | float | DHT22 溫度（°C）|
| `humidity` | float | DHT22 濕度（%）|
| `light_raw` | int | 光線感測器原始值（0–1023）|
| `light_is_bright` | bool | 是否超過亮度閾值 |
| `presence` | str | "OCCUPIED" / "UNOCCUPIED" / "UNKNOWN" |
| `presence_score` | float | 占用計分 |
| `weather_current` | dict | 目前天氣 JSON |
| `weather_forecast` | list | 5 天預報列表 |
| `weather_fetched_at` | datetime | 最後 fetch 時間 |
| `last_door_event` | dict | 最近門事件 |
| `last_face_event` | dict | 最近人臉事件 |
| `last_alert` | dict | 最近安全告警 |
| `display_busy` | bool | e-Paper 忙碌標誌 |
| `active_reminder` | str | 當前提醒文本 |
| `claude_usage_5h` | int | Claude 5h 使用百分比 |
| `claude_usage_week` | int | Claude 週使用百分比 |
| `codex_usage_5h` | int | Codex 5h 使用百分比 |
| `codex_usage_week` | int | Codex 週使用百分比 |
| `claude_reset_5h` | str | Claude 5h 重置時間 |
| `codex_reset_5h` | str | Codex 5h 重置時間 |
| `codex_reset_week` | str | Codex 週重置時間 |
| `started_at` | datetime | 服務啟動時間戳 |

---

## 硬體抽象模式

所有硬體元件使用 **Protocol + Factory** 模式：

```python
class DHT22Sensor(Protocol):
    def read(self) -> tuple[float, float]: ...

class RealDHT22:   # Pi 硬體版本（需 adafruit-circuitpython-dht）
    ...

class MockDHT22:   # 開發 / 測試版本（回傳固定值）
    def read(self) -> tuple[float, float]:
        return 26.0, 60.0

def create_dht22(config) -> DHT22Sensor:
    return MockDHT22() if config.use_mock else RealDHT22(config)
```

此模式讓單元測試完全不需要硬體，`RPI_MOCK=1` 環境變數或 `use_mock: true` 設定即可切換。

---

## 資料庫結構

SQLite（WAL 模式）位於 `data/epaper-home-display.db`：

| 資料表 | 說明 |
|-------|------|
| `indoor_env_logs` | 溫濕度、光線定期紀錄 |
| `presence_logs` | 占用狀態與計分紀錄 |
| `door_events` | 門狀態事件（來自 MQTT）|
| `face_events` | 人臉辨識事件（來自 MQTT）|
| `alarm_decisions` | 告警決策紀錄 |
| `system_events` | 系統級事件（info / warning / error）|
| `weather_logs` | 天氣資料快取 |
| `ai_usage_logs` | AI 使用量日誌 |

---

## WebUI 端點

FastAPI 服務執行於埠 `8000`，完整 API 說明見 [docs/webui.md](webui.md)：

**讀取端點（GET）**

| 路徑 | 說明 |
|------|------|
| `/settings` | HTML 設定介面（含 Leaflet 互動地圖）|
| `/health` | 健康檢查（`{"status": "ok"}`）|
| `/state` | 目前 AgentState 的 JSON 快照 |
| `/logs/env` | 環境日誌（溫濕度、光線）最近 50 筆 |
| `/logs/presence` | 占用度日誌最近 50 筆 |
| `/logs/events` | 系統事件日誌最近 50 筆 |
| `/settings/config` | 讀取配置（secret 遮罩為 boolean）|
| `/settings/wifi` | 取得 WiFi 連線資訊 |

**設定更新端點（PUT）**

| 路徑 | 參數 | 說明 |
|------|------|------|
| `/settings/location` | `lat`, `lon` | 更新天氣位置 |
| `/settings/weather` | `api_key`, `units`, `fetch_interval_seconds` | 更新天氣設定 |
| `/settings/mqtt` | `broker_host`, `broker_port`, `client_id` | 更新 MQTT 連線 |
| `/settings/display` | `model`, `dashboard_trigger_second`, `full_refresh_every` | 更新 e-Paper 參數 |
| `/settings/presence` | `light_weight`, `door_weight`, `face_weight`, `threshold`, `door_window_seconds`, `face_window_seconds` | 更新占用度計分參數 |
| `/settings/voice` | `enabled`, `player` | 更新語音設定 |
| `/settings/notifications` | `discord_webhook_url` | 更新 Discord Webhook |
| `/settings/general` | `timezone` | 更新時區 |

**資料接收端點（POST）**

| 路徑 | 說明 |
|------|------|
| `/ai_usage` | 接收 ai-usage-collector 推送的 AI 使用量資料 |

所有 PUT 端點變更會原子化寫入 `config.local.yaml`，重啟服務後生效。

---

## 配置優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

`config.local.yaml` 用於本機開發覆蓋，不需要完整列出所有選項，只寫需要覆蓋的部分即可。

> **注意**：唯一支援的環境變數覆蓋是 `RPI_MOCK=1`（強制 mock 所有硬體）。其他設定項目不支援環境變數覆蓋。
