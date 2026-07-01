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
│   │   ├── epaper.py        # e-Paper 驅動包裝（importlib 動態載入 waveshare_epd.{model}；Real + Mock）
│   │   ├── renderer.py      # 主渲染入口（800×480 Pillow RGB 圖像）
│   │   ├── renderer_cards.py   # 各卡片繪製函數（儀表板）
│   │   ├── renderer_alert.py   # 告警頁面渲染（安全事件 + 快照）
│   │   ├── renderer_apmode.py  # WiFi AP 熱點引導頁面渲染
│   │   ├── renderer_constants.py  # 解析度、顏色（RGB）、版面常數
│   │   ├── renderer_utils.py    # 天氣圖示、進度條等工具函數
│   │   └── image_processor.py  # 圖片裁切、旋轉/翻轉、Floyd-Steinberg dithering（六色量化）
│   │                            # 注意：硬體面板為七色 ACeP，但驅動的 Orange slot 目前映射至 Black，
│   │                            # 因此自訂圖片量化只使用六個有效色（黑/白/紅/黃/藍/綠）
│   ├── logic/
│   │   ├── presence.py      # 占用偵測（純函數，光線 → OCCUPIED/UNOCCUPIED）
│   │   ├── alarm_decision.py  # 安全告警決策引擎（純函數）
│   │   ├── desk_session.py  # 桌面工作時段狀態機（純函數）
│   │   ├── reminder.py      # 天氣提醒生成（純函數，用於 AI 語音提醒）
│   │   └── door_reminder.py # 開門天氣提醒文字生成（純函數，門開時 TTS 播報）
│   ├── sensors/
│   │   ├── dht22.py         # DHT22 溫濕度（Real + Mock）
│   │   ├── light_sensor.py  # MCP3008 ADC + 光敏電阻（Real + Mock）
│   │   └── button.py        # 4 鍵 GPIO 按鈕（gpiozero MultiButton / MockButton）
│   ├── services/
│   │   ├── mqtt_client.py   # Paho MQTT Pub/Sub
│   │   ├── weather.py       # OpenWeatherMap API（aiohttp）
│   │   ├── voice.py         # aplay 音效播放
│   │   ├── discord.py       # Discord Webhook 通知
│   │   ├── notification_manager.py  # 通知協調（裝置上線、時段結束、每日摘要）
│   │   ├── snapshot_client.py  # 外部攝影機快照擷取（aiohttp，共享 session）
│   │   ├── claude_usage.py  # Claude OAuth API 客戶端（token 刷新、使用量解析）
│   │   ├── codex_usage.py   # Codex OAuth API 客戶端（token 刷新、使用量解析）
│   │   └── wifi_monitor.py  # WiFi 狀態監測（client/ap/unknown，讀 /tmp/epaper-ap-mode.json）
│   ├── loops/               # asyncio 協程（由 main.py 以 gather 並行執行）
│   │   ├── sensor.py        # 感測器讀取循環（30 秒）
│   │   ├── presence.py      # 占用計分循環（60 秒）
│   │   ├── display.py       # 顯示更新循環（牆鐘 :57）
│   │   ├── weather.py       # 天氣更新循環（600 秒）
│   │   ├── claude_usage.py  # Claude 使用量輪詢循環（600 秒，OAuth API 直接拉取）
│   │   ├── codex_usage.py   # Codex 使用量輪詢循環（600 秒，OAuth API 直接拉取）
│   │   ├── notification.py  # 通知排程循環
│   │   └── button.py        # 按鈕事件處理
│   ├── storage/
│   │   ├── db.py            # SQLite 初始化（WAL 模式）
│   │   ├── logs.py          # 非同步日誌記錄公開 API
│   │   ├── _log_events.py   # 系統事件日誌
│   │   ├── _log_helpers.py  # 日誌工具函數
│   │   ├── _log_images.py   # 圖片元數據日誌與管理
│   │   ├── _log_notifications.py  # 通知日誌
│   │   ├── _log_sessions.py      # 桌面工作時段日誌
│   │   └── _log_env_analytics.py # 環境分析查詢（日/月/年聚合、今日極值）
│   └── webui/
│       ├── server.py        # FastAPI 應用工廠（注入所有路由）
│       ├── models.py        # Pydantic 請求/回應模型
│       ├── middleware.py    # 認證中介層（Session cookie 驗證）
│       ├── config_helpers.py  # config.local.yaml 讀寫工具
│       └── routes/
│           ├── auth.py      # 登入/登出（Session cookie）
│           ├── read_only.py # /health, /state, /logs/*, /api/preview/alert
│           ├── settings.py  # 設定 PUT 端點
│           ├── wifi.py      # AP 熱點入口（/wifi portal、/api/wifi/scan、/api/wifi/connect，不需認證）
│           ├── desk.py      # 桌面工作時段 REST API
│           ├── environment.py  # 環境溫濕度分析（/environment、/api/env/*）
│           └── images.py    # 圖片上傳/裁切/確認/輪播管理
├── tests/                   # pytest 單元測試（mock 硬體）
├── scripts/                 # Pi 硬體獨立測試腳本
├── lib/waveshare_epd/       # Waveshare 驅動（已內建：epd7in3e.py + epdconfig.py）
├── systemd/                 # systemd 服務單元
├── tools/
│   ├── claude_auth.py       # Claude OAuth 初次授權工具（在筆電執行）
│   └── codex_auth.py        # Codex OAuth 初次授權工具（在筆電執行）
├── docs/                    # 文件
├── assets/                  # 字體、音效、圖片資源
├── data/                    # SQLite 資料庫與圖片（git ignored）
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
Agent1 / 攝影機發布：
  home/security/door    ──┐
  home/security/face    ──┤
  home/security/alert   ──┼──► mqtt_client.py ──► state.py ──► logic/ ──► 發布：
  home/security/status  ──┤                                              home/home_state/presence       每 60 秒
  home/security/camera  ──┘ (raw JPEG, binary)  → state.last_snapshot_image     home/home_state/alarm_decision 決策改變時
                                                 state.last_camera_frame_bytes  home/home_state/alarm_command  Button 3/4 按下時
                                                 (WebUI /api/mqtt/camera/latest) home/display/status           每次 e-Paper 成功更新後
```

### 顯示更新觸發條件

```
牆鐘對齊（每 N 分鐘邊界，預設 5 分鐘）─────────────────────────┐
MQTT 告警事件（立即） ───────────────────────────────────────────┤
按鈕按下（立即） ───────────────────────────────────────────────┼──► display_queue ──► _display_loop ──► renderer ──► epaper
wifi_connected 事件（AP 結束後） ───────────────────────────────┘
```

> **MQTT camera frame**：只更新 `state.last_snapshot_image` / `last_camera_frame_bytes` / `last_camera_frame_at`，**不**放入 display_queue。Alert 頁面依牆鐘節奏排程，渲染時使用當下最新的快照。

---

## asyncio 協程架構

`app/main.py` 中以 `asyncio.gather()` 並行執行九個協程：

| 協程 | 觸發週期 | 職責 |
|------|---------|------|
| `_sensor_loop()` | 每 30 秒 | 讀 DHT22 + 光線感測器，更新 state |
| `_presence_loop()` | 每 60 秒 | 讀光線狀態 → `compute_presence()` → 桌面時段管理 + 告警決策；偵測到回家時立即喚醒 display_queue |
| `_display_loop()` | 牆鐘對齊（N 分鐘邊界，由 `dashboard_interval_minutes` 控制，預設每 5 分鐘）| 監聽 display_queue；無人在場時暫停更新；管理圖片輪播換圖（每 `carousel_interval_refreshes` 次刷新換圖）；告警頁面快照刷新 |
| `_weather_loop()` | 每 600 秒 | 非同步 fetch OpenWeatherMap → 更新 state 快取 |
| `_claude_usage_loop()` | 每 600 秒 | OAuth Bearer token 向 Anthropic API 拉取 Claude 5h/7d 使用量；token 過期時自動刷新 |
| `_codex_usage_loop()` | 每 600 秒 | OAuth Bearer token 向 OpenAI WHAM API 拉取 Codex 5h/7d 使用量；token 過期時自動刷新 |
| `_notification_loop()` | 依排程 | Discord 每日統計摘要等定時通知 |
| `_wifi_monitor_loop()` | 每 10 秒 | 讀取 `/tmp/epaper-ap-mode.json`；AP 模式時設定 `display_page = "ap_mode"`；AP 結束後送 `"wifi_connected"` 事件繞過在場偵測門禁，自動切回儀表板 |
| `server.serve()` | 持續 | FastAPI WebUI（埠 8000） |

**ThreadPoolExecutor**（3 個工作執行緒）用於阻擋性硬體 I/O（DHT22 感測、SPI 傳輸、e-Paper 驅動）。

**MQTT 執行緒安全**：Paho MQTT 在背景執行緒執行 `loop_start()`，回調透過 `asyncio.run_coroutine_threadsafe()` 安全轉至主 asyncio 循環。MQTT 不是 `asyncio.gather()` 中的協程，而是由 `MQTTService.start()` 啟動的獨立執行緒。

**按鈕**：gpiozero 按鈕回調在背景執行緒觸發，透過 `asyncio.run_coroutine_threadsafe()` 呼叫四個 async handler（`_handle_btn_dashboard` / `_handle_btn_alert_page` / `_handle_btn_trigger_alarm` / `_handle_btn_cancel_alarm`）。按鈕不是獨立的 asyncio 協程。

---

## e-Paper 更新策略

電子紙刷新很慢，絕不可阻擋 MQTT 回調或 WebUI 處理程式：

| 更新類型 | 觸發 | 說明 |
|---------|------|------|
| 一般更新 | 牆鐘 N 分鐘邊界（僅 OCCUPIED）| 在邊界前 `(60 - trigger_second)` 秒觸發；trigger_second 由 model 推導（epd7in3e→40, epd7in5_V2→57）|
| 完整更新（`init`）| 每 `full_refresh_every` 次更新 | 驅動有 `init_fast()` 時才有意義；`epd7in3e` 驅動每次均為完整刷新 |
| 告警立即更新 | MQTT 告警事件（`home/security/alert`）| 透過 display_queue；camera frame 只更新 state 欄位，不觸發 display_queue |
| 回家立即更新 | 光線變暗（UNOCCUPIED→OCCUPIED）| `_presence_loop` 偵測到後立即觸發 |
| AP 模式頁面 | 每 30 秒 | 靜態資訊頁，定期刷新時間戳 |
| 人不在時 | — | `display_loop` 暫停，不做任何更新（wifi_connected 事件可繞過此限制）|

> **注意**：`epd7in3e` 驅動無 `init_fast()` 方法，`epaper.py` 的 AttributeError fallback 會使每次更新均執行完整初始化。`full_refresh_every` 設定目前對 epd7in3e 面板效果等同於每次全刷新。

**牆鐘對齊原理**：`dashboard_interval_minutes`（預設 5）決定多久刷新一次，`dashboard_trigger_second` 由 model 推導（不可手動設定）。系統在每個 N 分鐘邊界前提早 `(60 - trigger_second)` 秒觸發，讓面板完成刷新時剛好顯示正確時間。例如：epd7in3e 在 :40 觸發，全刷新約 20 秒，面板在 :00 顯示正確分鐘數。

---

## 在場偵測邏輯

`app/logic/presence.py` 中的純函數 `compute_presence()`：

```
使用場景：電腦桌/辦公桌前，室內燈讓環境光讀值偏低；白天自然光高表示無人在家

if not light_is_bright:  → OCCUPIED  (score = 1.0)
else:                    → UNOCCUPIED (score = 0.0)

光線閾值由 sensors.light.bright_threshold 控制（預設 500 / ADC 0–1023）
```

**顯示行為**：
- OCCUPIED：正常每分鐘觸發秒更新
- UNOCCUPIED：display_loop 暫停，不刷新面板
- UNOCCUPIED → OCCUPIED：_presence_loop 立即送 display_queue，面板馬上更新

---

## 安全告警決策

`app/logic/alarm_decision.py` 中的純函數 `compute_alarm_decision()`：

```
if presence ∈ {UNOCCUPIED, UNKNOWN} AND 最近無已知人臉  →  TRIGGER_ALARM
elif presence == OCCUPIED AND 有已知人臉                →  CANCEL_ALARM
else                                                    →  NO_ACTION
```

決策結果發布至 `home/home_state/alarm_decision`，鍵名為 `alarm_decision`（非 `decision`）。

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

## 開門天氣提醒

`app/logic/door_reminder.py` 中的純函數 `generate_door_exit_text()`，由 MQTT 客戶端在偵測到 `closed → open` 門狀態轉換時呼叫，觸發條件與文字格式如下：

**格式**：`[現在 X度，天氣][，warning1][，warning2]`（最多兩項提醒；天氣簡報固定前置）

| 判斷條件（按優先度）| 提醒文字 |
|----------|---------|
| 未來 ~12 小時有雨（pop ≥ 0.6 或 OWM 代碼屬雨）| `記得帶雨傘` |
| feels_like < 15°C | `今天比較冷，記得穿外套` |
| 目前溫度 > 30°C | `外面很熱，注意防曬` |
| 未來 12 小時溫度下降 > 5°C | `稍後溫度會下降，帶件外套` |

**門控保護**：
- 冷卻 60 秒（防止門彈跳重複觸發）
- 15 秒內有任何人臉事件（known 或 unknown），不播報（表示有人在門口，非離家）
- 無人臉 sentinel（`"NONE"` / `"no_face"`）到達且門為開啟狀態時，重試播報
- 無天氣資料時播報固定備援文字：`出門注意安全`

---

## 全局狀態（AgentState）

`app/state.py` 定義的全局單例 `state = AgentState()`，被所有模組引用：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `temperature` | float \| None | DHT22 溫度（°C）|
| `humidity` | float \| None | DHT22 濕度（%）|
| `light_raw` | int \| None | 光線感測器原始值（0–1023）|
| `light_is_bright` | bool | 是否超過亮度閾值 |
| `presence` | str | "OCCUPIED" / "UNOCCUPIED" / "UNKNOWN" |
| `presence_score` | float | 占用計分（0.0 或 1.0）|
| `desk_session_id` | int \| None | 當前桌面工作時段 DB ID |
| `desk_session_start` | datetime \| None | 當前時段開始時間 |
| `weather_current` | dict \| None | 目前天氣 JSON |
| `weather_forecast` | list[dict] | 5 天預報列表 |
| `weather_fetched_at` | datetime \| None | 最後 fetch 時間 |
| `last_door_event` | dict \| None | 最近門事件（含正規化後的 `state` 與 `door_state` 欄位）|
| `last_face_event` | dict \| None | 最近人臉事件（身份統一寫入 `identity` 與 `user_name`）|
| `last_face_event_at` | datetime \| None | 最近有效人臉事件的時間戳（無人臉 sentinel 到達時設為 `None`，供開門提醒門控使用）|
| `last_alert` | dict \| None | 最近安全告警 |
| `last_alarm_decision` | str \| None | 最近告警決策字串（`"TRIGGER_ALARM"` / `"NO_ACTION"` / `"CANCEL_ALARM"`）|
| `alert_face_event` | dict \| None | 告警觸發當下的人臉事件快照（與 `last_face_event` 解耦，避免後續人臉更新影響告警頁面）|
| `security_status` | dict \| None | Agent 1 狀態心跳（`home/security/status` payload）|
| `mqtt_connected` | bool | Paho MQTT 連線狀態（`on_connect` / `on_disconnect` 回調更新）|
| `mqtt_last_rx_by_topic` | dict | 各 JSON 訂閱主題最後收到的訊息（key=topic）；camera binary 不計入 |
| `mqtt_rx_log` | list | 最近 50 筆收到的 JSON MQTT 訊息（newest first）；camera binary 不計入 |
| `mqtt_tx_log` | list | 最近 20 筆發出的 MQTT 訊息（newest first）|
| `display_busy` | bool | e-Paper 忙碌標誌 |
| `active_reminder` | str \| None | 當前提醒文本 |
| `custom_image_path` | str \| None | 當前顯示的圖片路徑 |
| `image_playlist` | list[str] | 已確認圖片的完整路徑清單 |
| `carousel_index` | int | 輪播當前索引 |
| `carousel_refresh_count` | int | 距上次換圖的 dashboard 刷新計數（達到 `carousel_interval_refreshes` 時換圖）|
| `carousel_skip_next_advance` | bool | one-shot 旗標：WebUI 手動換圖後設為 `True`，下一次 dashboard 渲染前的自動換圖判斷會消耗此旗標並跳過（不遞增計數、不再次換圖），確保手動選中的圖片至少顯示一次 |
| `claude_usage_5h` | float \| None | Claude 5h 使用率（0.0–1.0）|
| `claude_usage_week` | float \| None | Claude 週使用率（0.0–1.0）|
| `codex_usage_5h` | float \| None | Codex 5h 使用率（0.0–1.0）|
| `codex_usage_week` | float \| None | Codex 週使用率（0.0–1.0）|
| `claude_5h_reset` | str \| None | Claude 5h 重置時間（HH:MM 格式）|
| `claude_7d_reset` | str \| None | Claude 7d 剩餘時間（如 `"2d 3h"`）|
| `codex_5h_reset` | str \| None | Codex 5h 重置時間（HH:MM 格式）|
| `codex_7d_reset` | str \| None | Codex 7d 剩餘時間（如 `"2d 3h"`）|
| `display_page` | Literal["dashboard", "alert", "ap_mode"] | 目前顯示頁面 |
| `last_snapshot_image` | Any（PIL Image \| None）| 最後取得的攝影機影像（MQTT camera feed 或 HTTP snapshot；型別標注為 Any，實際為 PIL Image，僅記憶體，不序列化）|
| `last_camera_frame_bytes` | bytes \| None | 最後一次 MQTT camera frame 的原始 JPEG bytes（供 WebUI `GET /api/mqtt/camera/latest` 直接轉發，不需重新編碼）|
| `last_camera_frame_at` | datetime \| None | 最後一次收到 MQTT camera frame 的時間戳（用於判斷影像新鮮度：5 秒內視為新鮮，優先於 HTTP snapshot）|
| `alert_page_started_at` | datetime \| None | 告警頁面首次進入時間（由 MQTT callback 設定，僅在非 alert 狀態時更新）|
| `alert_last_triggered_at` | datetime \| None | 最後一次告警觸發時間（**用於超時計算**：超過 `alert_page_timeout_sec` 後切回儀表板）|
| `alert_dismissed_at` | datetime \| None | 最後一次告警頁面關閉時間（用於 180 秒冷卻計算，防止快速重複觸發）|
| `wifi_mode` | Literal["client", "ap", "unknown"] | WiFi 模式 |
| `ap_ssid` | str | AP 熱點 SSID（AP 模式下顯示）|
| `ap_password` | str | AP 熱點密碼（AP 模式下顯示）|
| `ap_ip` | str | AP 熱點 IP（AP 模式下顯示，通常 10.42.0.1）|
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
| `desk_sessions` | 桌面工作時段記錄（start/end/duration）|
| `images` | 圖片元數據與路徑（tmp_path / display_path）|
| `notification_queue` | 通知發送佇列（含 attempts、next_retry_ts、sent，支援重試）|

---

## WebUI 端點

FastAPI 服務執行於埠 `8000`，完整 API 說明見 [docs/webui.md](webui.md)。WebUI 受密碼保護（Session cookie 認證）。

**認證**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 已登入時重新導向至 `/settings`；未登入的瀏覽器請求導向 `/login?next=/`；非 HTML 請求回傳 `401` |
| GET | `/login` | 登入頁面（首次使用時顯示密碼設定表單）|
| POST | `/login` | 提交密碼，成功後 redirect 至目標頁面 |
| GET | `/logout` | 清除 session，redirect 至 `/login` |

**讀取端點（GET）**

| 路徑 | 說明 |
|------|------|
| `/settings` | HTML 設定介面（含 Leaflet 互動地圖）|
| `/images` | HTML 圖片管理介面 |
| `/desk` | HTML 桌面工作時段介面 |
| `/environment` | HTML 環境溫濕度分析介面（日/月/年圖表）|
| `/mqtt` | HTML MQTT 監控介面（顯示連線狀態、收發日誌、攝影機畫面）|
| `/health` | 健康檢查（`{"status": "ok"}`，不需認證）|
| `/state` | AgentState 部分欄位快照（感測器、天氣、安全事件、AI 使用量；不含 MQTT 連線狀態與日誌，見 `/api/mqtt/status`）|
| `/logs/env` | 環境日誌（溫濕度、光線）最近 50 筆 |
| `/logs/presence` | 占用度日誌最近 50 筆 |
| `/logs/events` | 系統事件日誌最近 50 筆 |
| `/api/env/current` | 目前溫濕度 + 今日極值（min/max/avg）|
| `/api/env/chart?scale=day\|month\|year&ref=...` | 環境歷史圖表資料（日/月/年聚合）|
| `/api/env/years` | 資料庫中有資料的年份清單 |
| `/settings/config` | 讀取配置（`api_key`→`api_key_set`、`webhook_url`→`webhook_set`、`mqtt.password`→`password_set` 遮罩為 boolean；`password_hash`/`session_secret` 移除）|
| `/settings/wifi` | 取得 WiFi 連線資訊（SSID、IP、訊號強度）|
| `/wifi` | AP 熱點入口網站（`wifi.py`，不需認證）|
| `/api/wifi/scan` | 掃描周邊 WiFi 網路（GET，AP 模式限定，不需認證）|
| `/api/preview/alert` | 回傳告警頁面的 PNG 預覽（debug 用，**需認證**）|
| `/api/mqtt/status` | MQTT 連線狀態 JSON（含收發日誌、最後 camera frame 時間戳）|
| `/api/mqtt/camera/latest` | 最新 MQTT camera frame（JPEG，204 表示無可用畫面）|

**WiFi AP 管理端點（POST，不需認證）**

| 路徑 | 說明 |
|------|------|
| `/api/wifi/connect` | 連接指定 WiFi 網路（AP 模式限定）；兩階段：Phase 1 建立 NM 設定檔（同步），Phase 2 啟動連線（背景任務）|

**設定更新端點（PUT）**

| 路徑 | 說明 |
|------|------|
| `/settings/location` | 更新天氣位置（`lat`, `lon`）|
| `/settings/weather` | 更新天氣設定 |
| `/settings/mqtt` | 更新 MQTT 連線 |
| `/settings/display` | 更新 e-Paper 參數 |
| `/settings/presence` | 更新光線閾值（`bright_threshold`）|
| `/settings/voice` | 更新語音設定 |
| `/settings/notifications` | 更新 Discord Webhook |
| `/settings/general` | 更新時區 |
| `/settings/auth` | 修改 WebUI 密碼（需提供目前密碼驗證）|

**圖片管理（Images）**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/images` | 列出所有已確認圖片 |
| POST | `/api/images/upload` | 上傳圖片（返回 id 與原始尺寸）|
| POST | `/api/images/preview` | 產生裁切+dithering 預覽（返回 PNG）|
| POST | `/api/images/{id}/confirm` | 確認裁切設定，生成 display PNG 並更新輪播 |
| DELETE | `/api/images/{id}` | 刪除圖片 |
| GET | `/api/images/file/{id}` | 提供 display PNG 檔案 |
| GET | `/api/images/original/{id}` | 提供原始上傳檔案 |
| GET | `/api/images/carousel` | 讀取輪播設定 |
| PUT | `/api/images/carousel` | 更新輪播設定（enabled/interval/mode）|
| PUT | `/api/images/carousel/advance` | 手動切換輪播圖片（僅更新狀態，不強制 e-Paper 立即刷新）|

**桌面工作時段（Desk）**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/desk/stats` | 今日統計（在場狀態、總時長、時段數）|
| GET | `/api/desk/history` | 近 24 小時時間軸 + 近 30 天每日統計 |
| GET | `/api/desk/sessions` | 最近 N 筆時段記錄（預設 20 筆）|

所有 PUT /settings/* 端點變更會原子化寫入 `config.local.yaml`，並同時更新記憶體中的設定物件。**天氣、顯示器、在場偵測、語音、Discord 通知、時區、密碼**等設定立即生效（下次排程執行時採用新值）。**MQTT** 設定雖寫入 YAML，但現有連線不會自動重建，需重啟服務才生效。

---

## 配置優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

`config.local.yaml` 用於本機開發覆蓋，不需要完整列出所有選項，只寫需要覆蓋的部分即可。

> **注意**：唯一支援的環境變數覆蓋是 `RPI_MOCK=1`（強制 mock 所有硬體）。其他設定項目不支援環境變數覆蓋。`display.dashboard_trigger_second` 不可手動設定，由 `display.model` 自動推導（epd7in3e→40, epd7in5_V2→57, mock→57）。
