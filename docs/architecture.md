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
│  Services (app/services/)               │  天氣 API, 音效, Discord
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
│   │   ├── dirty_region.py  # 畫面 diff → 局部刷新矩形計算（純函數，僅 epd7in5_V2 用得到）
│   │   ├── renderer.py      # 主渲染入口（800×480 Pillow RGB 圖像）
│   │   ├── renderer_cards.py   # 各卡片繪製函數（儀表板）
│   │   ├── renderer_apmode.py  # WiFi AP 熱點引導頁面渲染
│   │   ├── renderer_constants.py  # 解析度、顏色（RGB）、版面常數
│   │   ├── renderer_utils.py    # 天氣圖示、進度條等工具函數
│   │   └── image_processor.py  # 圖片裁切、旋轉/翻轉、Floyd-Steinberg dithering（六色量化）
│   │                            # 注意：硬體面板為七色 ACeP，但驅動的 Orange slot 目前映射至 Black，
│   │                            # 因此自訂圖片量化只使用六個有效色（黑/白/紅/黃/藍/綠）
│   ├── logic/
│   │   ├── presence.py      # 占用偵測（純函數，光線 → OCCUPIED/UNOCCUPIED）
│   │   ├── desk_session.py  # 桌面工作時段狀態機（純函數）
│   │   ├── reminder.py      # 天氣提醒生成（純函數，用於 AI 語音提醒）
│   │   └── hydration.py     # HydraCup MQTT payload 解析（純函數，parse_status）
│   ├── sensors/
│   │   ├── dht22.py         # DHT22 溫濕度（Real + Mock）
│   │   ├── light_sensor.py  # MCP3008 ADC + 光敏電阻（Real + Mock）
│   │   └── button.py        # 4 接腳 GPIO 按鈕（gpiozero MultiButton / MockButton）；僅 Button 1 綁定功能，2–4 保留接腳未綁定
│   ├── services/
│   │   ├── weather.py       # OpenWeatherMap API（aiohttp）
│   │   ├── voice.py         # aplay 音效播放（目前未被任何事件觸發，供 WebUI 手動測試音效使用）
│   │   ├── discord.py       # Discord Webhook 通知
│   │   ├── notification_manager.py  # 通知協調（裝置上線、時段結束、每日摘要）
│   │   ├── claude_usage.py  # Claude OAuth API 客戶端（token 刷新、使用量解析）
│   │   ├── codex_usage.py   # Codex OAuth API 客戶端（token 刷新、使用量解析）
│   │   ├── wifi_monitor.py  # WiFi 狀態監測（client/ap/unknown，讀 /tmp/epaper-ap-mode.json）
│   │   └── mqtt_client.py   # HydraCup MQTT 訂閱服務（paho-mqtt，見下方「HydraCup MQTT 資料流」）
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
│       ├── middleware.py    # 認證中介層（server-side session + CSRF 驗證）
│       ├── config_helpers.py  # config.local.yaml 讀寫工具
│       └── routes/
│           ├── auth.py      # 登入/登出（單一 server-side session slot）
│           ├── read_only.py # /health, /state, /logs/*
│           ├── settings.py  # 設定 PUT 端點
│           ├── wifi.py      # AP 熱點入口（首次設定公開；已設定裝置需 session + CSRF）
│           ├── desk.py      # 桌面工作時段 REST API
│           ├── environment.py  # 環境溫濕度分析（/environment、/api/env/*）
│           └── images.py    # 圖片上傳/裁切/確認/輪播管理
├── tests/                   # pytest 單元測試（mock 硬體）
├── scripts/                 # Pi 硬體獨立測試腳本
├── lib/waveshare_epd/       # Waveshare 驅動（已內建：epdconfig.py + epd7in3e.py + epd7in5_V2.py）
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

### HydraCup MQTT 資料流

```
esp32-hydracup ──► Mosquitto broker (Pi, :1883) ──► app/services/mqtt_client.py（paho-mqtt，獨立背景執行緒）
    ──► app/logic/hydration.py::parse_status()（純函數）──► state.py（hydra_*）──► renderer_cards.py::_draw_card_hydra()
```

`MQTTService` 不是 `asyncio.gather()` 中的協程——paho-mqtt 用自己的 `loop_start()` 背景執行緒處理網路 I/O，收到訊息後透過 `asyncio.run_coroutine_threadsafe()` 把 dispatch 丟回主 event loop 更新 `state`。`.start(loop)` 在 `app/main.py` 的 `try` 區塊內、`await asyncio.gather(...)` 之前呼叫；`.stop()` 在 `finally` 區塊呼叫。完整協議規格（topic、payload schema、QoS、發布時機）見 [docs/hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md)。

### 顯示更新觸發條件

```
牆鐘對齊（每 N 分鐘邊界，預設 5 分鐘）─────────────────────────┐
按鈕按下（立即） ───────────────────────────────────────────────┼──► display_queue ──► _display_loop ──► renderer ──► epaper
wifi_connected 事件（AP 結束後） ───────────────────────────────┘
presence_return 事件（UNOCCUPIED → OCCUPIED，立即）────────────┘
```

---

## asyncio 協程架構

`app/main.py` 中以 `asyncio.gather()` 並行執行九個協程：

| 協程 | 觸發週期 | 職責 |
|------|---------|------|
| `_sensor_loop()` | 每 30 秒 | 讀 DHT22 + 光線感測器，更新 state |
| `_presence_loop()` | 每 60 秒 | 讀光線狀態 → `compute_presence()` → 桌面時段管理；偵測到回家時立即喚醒 display_queue |
| `_display_loop()` | 牆鐘對齊（N 分鐘邊界，由 `dashboard_interval_minutes` 控制，預設每 5 分鐘）| 監聽 display_queue；無人在場時暫停更新；管理圖片輪播換圖（每 `carousel_interval_refreshes` 次刷新換圖）|
| `_weather_loop()` | 每 600 秒 | 非同步 fetch OpenWeatherMap → 更新 state 快取 |
| `_claude_usage_loop()` | 每 600 秒 | OAuth Bearer token 向 Anthropic API 拉取 Claude 5h/7d 使用量；token 過期時自動刷新 |
| `_codex_usage_loop()` | 每 600 秒 | OAuth Bearer token 向 OpenAI WHAM API 拉取 Codex 5h/7d 使用量；token 過期時自動刷新 |
| `_notification_loop()` | 依排程 | Discord 每日統計摘要等定時通知 |
| `_wifi_monitor_loop()` | 每 10 秒 | 讀取 `/tmp/epaper-ap-mode.json`；AP 模式時設定 `display_page = "ap_mode"`；AP 結束後送 `"wifi_connected"` 事件繞過在場偵測門禁，自動切回儀表板 |
| `server.serve()` | 持續 | FastAPI WebUI（埠 8000） |

**ThreadPoolExecutor**（3 個工作執行緒）用於阻擋性硬體 I/O（DHT22 感測、SPI 傳輸、e-Paper 驅動）。

**按鈕**：gpiozero 按鈕回調在背景執行緒觸發，透過 `asyncio.run_coroutine_threadsafe()` 呼叫 async handler `_handle_btn_dashboard`（Button 1，切到 dashboard 並設為 OCCUPIED）。Button 2–4 的 GPIO 接腳仍保留（`sensors.button.gpio_pins` 至少 4 個），但目前未綁定任何 callback。按鈕不是獨立的 asyncio 協程。

---

## e-Paper 更新策略

電子紙刷新很慢，絕不可阻擋 WebUI 處理程式：

| 更新類型 | 觸發 | 說明 |
|---------|------|------|
| 一般更新 | 牆鐘 N 分鐘邊界（僅 OCCUPIED）| 在邊界前 `(60 - trigger_second)` 秒觸發；trigger_second 由 model 推導（epd7in3e→40, epd7in5_V2→57）|
| 完整更新（`init`）| 每 `full_refresh_every` 次更新 | 驅動有 `init_fast()` 時才有意義；`epd7in3e` 驅動每次均為完整刷新 |
| 回家立即更新 | 光線變暗（UNOCCUPIED→OCCUPIED）| `_presence_loop` 偵測到後立即觸發 |
| AP 模式頁面 | 每 30 秒 | 靜態資訊頁，定期刷新時間戳 |
| 人不在時 | — | `display_loop` 暫停，不做任何更新（wifi_connected 事件可繞過此限制）|

> **注意**：`epd7in3e` 驅動無 `init_fast()` 方法，`epaper.py` 的 AttributeError fallback 會使每次更新均執行完整初始化。`full_refresh_every` 設定目前對 epd7in3e 面板效果等同於每次全刷新。

**dirty-region 局部刷新（僅 `epd7in5_V2`）**：非全刷新的更新不再無條件送出整張畫面。`RealEpaper`（`app/display/epaper.py`）會保留上一次成功寫入面板的畫面（`self._last_image`），呼叫 `app/display/dirty_region.compute_dirty_regions()` 跟本次要顯示的畫面比對，只把有變化的矩形區域透過 `init_part()` + `display_Partial()` 送到面板；畫面完全沒有變化時整次略過面板寫入（連 init 都不呼叫）。演算法把畫面切成 40px 網格做 4-連通分群，最多回傳 6 個獨立矩形（`MAX_REGIONS`），超過就退化成單一涵蓋所有變化像素的矩形，避免過多 `display_Partial()` 呼叫各自的 busy-wait 開銷反而比全刷新慢（`init_part()` 每次 `display()` 只呼叫一次，region 迴圈只重複呼叫 `display_Partial()`）；X 軸座標會對齊 8 的倍數（面板以 byte 定址）。以下情況會直接 fall through 到既有的 init_fast/全刷新路徑，不進 dirty-region 分支：尚未有上一張畫面（開機後第一次、或剛執行過 `clear()`）、畫面尺寸不是面板原生的 `(width, height)`（`getbuffer()` 的 480x800 自動旋轉在 dirty-region 路徑沒有對應處理）、或驅動沒有 `display_Partial()`/`init_part()`（`epd7in3e` 恆不受影響）。`app/display/dirty_region.pack_mono_buffer()` 反相 bit 的方式跟 `getbuffer()`完全一樣（`convert("1")` 後 XOR `0xFF`）——這是在真實 `epd7in5_V2` 面板上實測驗證過的結論。單純從 `display_Partial()` 原始碼推導（它內部會對傳入 buffer 做 `~Image[...]`）會得出「不應該預先反相，否則雙重反相」的結論，但這個推導在實機上被證實是錯的：不預先反相時，局部刷新的區域在真實面板上會出現黑白顛倒。以實機結果為準，不要只信原始碼推導。

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
| `hydra_current_ml` | int \| None | HydraCup 今日目前喝水量（毫升）|
| `hydra_goal_ml` | int \| None | HydraCup 今日目標飲水量（毫升）|
| `hydra_pct` | float \| None | HydraCup 完成比例。語意上是 0.0–1.0 的分數；payload 直接提供的 `pct` 欄位限制在 -10.0～10.0 之間（超出視為無效並改用下一項 fallback），缺失時 fallback 為 `current_ml / goal_ml`（兩者各自上限 9999，故 fallback 值理論上可超出 -10.0～10.0）；顯示時 `_draw_card_hydra()` 一律 clamp 到 0%–100% |
| `hydra_updated_at` | datetime \| None | 最後一次收到 `hydracup/status` 的時間（epaper-display 端收到時間，非裝置端時間戳）|
| `hydra_broker_connected` | bool | epaper-display 與 MQTT broker 的連線狀態 |
| `hydra_device_online` | bool | 由 `hydracup/availability`（含 LWT）回報的 HydraCup 裝置線上狀態 |
| `display_page` | Literal["dashboard", "ap_mode"] | 目前顯示頁面 |
| `wifi_mode` | Literal["client", "ap", "unknown"] | WiFi 模式 |
| `ap_ssid` | str | AP 熱點 SSID（AP 模式下顯示）|
| `ap_password` | str | AP 熱點密碼（AP 模式下顯示）|
| `ap_ip` | str | AP 熱點 IP（AP 模式下顯示，通常 10.42.0.1）|
| `started_at` | datetime | 服務啟動時間戳 |

### state 並發模型

`state` 是模組層級單例，被上方「asyncio 協程架構」列出的九個協程與 WebUI 路由共寫/共讀，全程沒有 lock。安全性建立在兩個前提上：

1. **單執行緒事件迴圈**：九個協程都在同一個 `asyncio.gather()` 下跑在同一條執行緒；Python 直譯器每次只執行一個協程的 bytecode，協程之間的切換只發生在 `await` 點。單一屬性的讀取或寫入（如 `state.temperature = 26.0`）之間不含 `await`，因此對其他協程而言是原子的，不會被插入執行到一半的狀態。
2. **背景執行緒一律經 `run_coroutine_threadsafe()` 交還事件迴圈**：`MQTTService`（HydraCup）與 `BambuMQTTService`（印表機）用 paho-mqtt 自己的 `loop_start()` 背景執行緒處理網路 I/O，收到訊息不會直接改 `state`，而是用 `asyncio.run_coroutine_threadsafe()` 把 dispatch 丟回主事件迴圈執行，回到前提 1 的單執行緒保證下再寫入。按鈕 GPIO 回調（gpiozero 背景執行緒）同樣經此模式呼叫 `_handle_btn_dashboard`（見 `app/main.py`）。

在此前提下，各協程遵守「各自擁有一組欄位、只有自己寫入」的慣例（例如 `_sensor_loop` 只寫 `temperature`/`humidity`/`light_*`，`_presence_loop` 只寫 `presence*`/`desk_session_*`），讀取端（`renderer.py`、WebUI 的 `/state`）只讀不寫，因此即使沒有 lock 也不會有兩個協程同時寫同一欄位的競爭；跨欄位的讀取快照理論上可能讀到「部分更新」的組合（例如渲染時 `hydra_current_ml` 已更新但 `hydra_pct` 還沒），但目前沒有任何欄位組合要求跨欄位原子性，因此可接受。

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
| `door_events` | *(legacy)* 已退役的 Agent 1 整合遺留 schema，程式碼不再寫入，僅保留避免刪除既有歷史資料 |
| `face_events` | *(legacy)* 同上 |
| `alarm_decisions` | *(legacy)* 同上 |
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
| POST | `/logout` | 驗證 CSRF 後清除 server-side session，redirect 至 `/login` |

**讀取端點（GET）**

| 路徑 | 說明 |
|------|------|
| `/settings` | HTML 設定介面（離線座標輸入、主題切換）|
| `/images` | HTML 圖片管理介面 |
| `/desk` | HTML 桌面工作時段介面 |
| `/environment` | HTML 環境溫濕度分析介面（日/月/年圖表）|
| `/health` | 健康檢查（`{"status": "ok"}`，不需認證）|
| `/state` | AgentState 部分欄位快照（感測器、天氣、AI 使用量、HydraCup 喝水資料）|
| `/logs/env` | 環境日誌（溫濕度、光線）最近 50 筆 |
| `/logs/presence` | 占用度日誌最近 50 筆 |
| `/logs/events` | 系統事件日誌最近 50 筆 |
| `/api/env/current` | 目前溫濕度 + 今日極值（min/max/avg）|
| `/api/env/chart?scale=day\|month\|year&ref=...` | 環境歷史圖表資料（日/月/年聚合）|
| `/api/env/years` | 資料庫中有資料的年份清單 |
| `/settings/config` | 讀取配置（`api_key`→`api_key_set`、`webhook_url`→`webhook_set` 遮罩為 boolean；`password_hash`/`session_secret` 移除）|
| `/settings/wifi` | 取得 WiFi 連線資訊（SSID、IP、訊號強度）|
| `/wifi` | AP 熱點入口網站（首次尚未設定密碼時公開；已設定裝置需登入）|
| `/api/wifi/scan` | 掃描周邊 WiFi 網路（GET，AP 模式限定；已設定裝置需登入）|

**WiFi AP 管理端點（首次設定公開但需要 pre-auth CSRF；已設定裝置需要 session CSRF）**

| 路徑 | 說明 |
|------|------|
| `/api/wifi/connect` | 連接指定 WiFi 網路（AP 模式限定、需 CSRF）；兩階段：Phase 1 建立 NM 設定檔（同步），Phase 2 啟動連線（背景任務）|

**設定更新端點（PUT）**

| 路徑 | 說明 |
|------|------|
| `/settings/location` | 更新天氣位置（`lat`, `lon`）|
| `/settings/weather` | 更新天氣設定 |
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
| GET | `/api/desk/status` | 即時狀態與感測器原始值（今日總時長、目前時段、切換次數）|
| GET | `/api/desk/timeline` | 近 24 小時時間軸 |
| GET | `/api/desk/daily` | 近 30 天每日彙總 |
| GET | `/api/desk/heatmap?year=YYYY` | 年度每日書桌前時間熱力圖（跨午夜切分、時區轉換、進行中時段計至現在）|
| GET | `/api/desk/sessions` | 最近 N 筆時段記錄（預設 20 筆）|

所有 PUT /settings/* 端點變更會原子化寫入 `config.local.yaml`，並同時更新記憶體中的設定物件，**天氣、顯示器、在場偵測、語音、Discord 通知、時區、密碼**等設定立即生效（下次排程執行時採用新值）。

---

## 配置優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

`config.local.yaml` 用於本機開發覆蓋，不需要完整列出所有選項，只寫需要覆蓋的部分即可。

> **注意**：唯一支援的環境變數覆蓋是 `RPI_MOCK=1`（強制 mock 所有硬體）。其他設定項目不支援環境變數覆蓋。`display.dashboard_trigger_second` 不可手動設定，由 `display.model` 自動推導（epd7in3e→40, epd7in5_V2→57, mock→57）。
