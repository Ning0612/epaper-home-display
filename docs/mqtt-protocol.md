# MQTT 協定規範

## 連線設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| Broker Host | `192.168.1.100`（範例） | 在 `config.yaml` 中設定；程式碼預設為 `localhost` |
| Port | `1883` | 標準 MQTT 埠 |
| Client ID | `epaper-home-display` | 識別本服務的客戶端 ID |
| QoS | `1` | 所有發布訊息使用 QoS 1（至少送達一次）|
| Username | `""` | 可選：Broker 帳號（`config.yaml` 的 `mqtt.username`）|
| Password | `""` | 可選：Broker 密碼（`config.yaml` 的 `mqtt.password`）|

**認證**：`mqtt.username` 非空時，服務會以 `client.username_pw_set()` 傳遞帳密給 Broker。Mosquitto 啟用 `password_file` 時必須設定此欄位；未啟用認證的 Broker 保持空字串即可。

---

## 訂閱主題（入站）

本服務訂閱以下主題，接收來自 **Agent 1** 的事件：

### `home/security/door` — 門狀態事件

門的開關狀態更新。

```json
{
  "door_state": "open",
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `door_state` | string | 優先讀取此欄位；舊版 Agent 1 可能使用 `state` 欄位，兩者均受支援 |
| `state` | string | 舊版相容欄位（與 `door_state` 二擇一，`door_state` 優先）|
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**正規化**：服務端會將原始值統一轉換為小寫，並移除 `door_` 前綴（例如 `"DOOR_OPEN"` → `"open"`，`"DOOR_CLOSED"` → `"closed"`）。

**效果**：
- 更新 `state.last_door_event`（內含正規化後的 `state` 與 `door_state` 欄位）
- 寫入 `door_events` 資料表
- 僅在偵測到 `closed → open` 狀態轉換時觸發開門天氣提醒（`_maybe_play_door_reminder()`）

---

### `home/security/face` — 人臉辨識事件

人臉辨識結果。

```json
{
  "vote_result": "lance",
  "known": true,
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `vote_result` | string | **主欄位（FaceGuard 協定）**：多幀投票後的最終身份結果（已知人員名稱、`"UNKNOWN"` 或 `"NONE"`）|
| `user_name` | string | 舊版相容欄位；`vote_result` 為空時作為 fallback |
| `identity` | string | 舊版相容欄位；`vote_result` 與 `user_name` 均為空時作為 fallback |
| `known` | bool | `true` = 已知人員；`false` = 陌生人（若省略，根據正規化後身份推導）|
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**身份欄位優先度**：`vote_result` → `user_name` → `identity`，均為空時預設為 `"NONE"`。

**正規化邏輯**：`known` 缺失時根據正規化後的身份自動推導。實作分兩層 sentinel：

| 身份值 | 語意 | `known` 推導 | `last_face_event_at` |
|--------|------|-------------|----------------------|
| `"NONE"` / `"no_face"` | 門口**無人臉**（攝影機未偵測到人）| `false` | 清除為 `None`（不阻擋開門提醒）|
| `"UNKNOWN"` / `""` | 偵測到人臉但**未識別** | `false` | 更新為當下時間（視為有人，阻擋開門提醒 15 秒）|
| 已知人員名稱 | 已識別人員 | `true` | 更新為當下時間 |

**`"NONE"` / `"no_face"` 特殊處理**：清除 `state.last_face_event_at`（使下次開門不受人臉時間戳門控阻擋）；若門當下已為開啟狀態，立即重試開門天氣提醒。`"UNKNOWN"` 不在此範圍，仍會阻擋提醒。

**效果**：
- 更新 `state.last_face_event`（身份統一正規化寫入 `identity` 與 `user_name` 欄位）
- 更新 `state.last_face_event_at`（有人臉時設為當下時間；無人臉時設為 `None`）
- 寫入 `face_events` 資料表
- **告警決策即時重算**：`compute_alarm_decision()` 在 `_presence_loop()` 中執行；收到 `home/security/alert` 後透過 `asyncio.Event` 立即喚醒 presence loop（無需等待 60 秒週期）；人臉事件到達後若有待決告警亦會在下一 presence 週期（最多 60 秒）反映至決策

---

### `home/security/alert` — 安全告警事件

觸發立即顯示更新（不等待牆鐘對齊）。

```json
{
  "alert_type": "UNKNOWN_CONFIRMED",
  "alert_level": "ALERT_YELLOW",
  "timestamp": "2026-05-29T10:30:00",
  "agent": "FaceGuard"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `alert_type` | string | 告警類型，如 `"UNKNOWN_CONFIRMED"`, `"motion"` |
| `alert_level` | string | 嚴重程度，如 `"ALERT_YELLOW"`, `"ALERT_RED"` |
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**效果**：
- 更新 `state.last_alert`、`state.alert_last_triggered_at`、`state.alert_face_event`（快照當前人臉事件）
- 設定 `state.display_page = "alert"` 並立即觸發 `display_queue.put_nowait("alert")`
- 渲染條件：僅在 `outdoor_agent.alert_page_enabled: true` 時渲染告警頁面；否則 `_check_alert_timeout()` 立即重置 `display_page = "dashboard"`
- 播放 `alert.wav` 音效（USB 喇叭，需 `voice.enabled: true` 且 `assets/sounds/alert.wav` 存在）
- Discord 告警通知由 **Agent 1** 負責發送，本服務不發送
- **冷卻機制**：若告警頁面剛被關閉（`alert_dismissed_at` 記錄），180 秒內收到新告警會靜默忽略（防止快速循環觸發）

---

### `home/security/status` — Agent 1 狀態

Agent 1 的系統狀態心跳。

```json
{
  "status": "online",
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

**效果**：
- 更新 `state.security_status`
- 顯示於 e-Paper 面板的「Agent1 狀態」區塊

---

### `home/security/camera` — 即時攝影機畫面

來自外部攝影機的即時 JPEG 影像串流（**raw binary，非 JSON**）。

| 屬性 | 值 | 說明 |
|------|-----|------|
| QoS | 0 | 儘力送達，可能遺失，不重傳 |
| 酬載格式 | raw JPEG bytes | 必須以 `\xff\xd8`（JPEG SOI marker）開頭 |
| 大小限制 | 最大 64 KB | FaceGuard 規格最大 48 KB；超過則靜默丟棄 |

**效果**：
- 解碼 JPEG → 轉換為 RGB PIL Image → 更新 `state.last_snapshot_image`
- 保留原始 JPEG bytes → 更新 `state.last_camera_frame_bytes`（供 WebUI `GET /api/mqtt/camera/latest` 直接轉發，無需重新編碼）
- 更新 `state.last_camera_frame_at`（時間戳，用於判斷影像新鮮度）
- **不觸發** `display_queue` 排隊；alert 頁面的 e-Paper 渲染依照牆鐘對齊節奏自動排程，渲染時使用當下最新的 `last_snapshot_image`
- **不記錄**到 `state.mqtt_rx_log` / `state.mqtt_last_rx_by_topic`（binary 幀不走 JSON dispatch）

> **與 HTTP snapshot 的關係**：告警頁面優先使用 MQTT 攝影機畫面（`last_camera_frame_at` 在 5 秒內視為新鮮）；若 MQTT 無新鮮畫面且 `outdoor_agent.snapshot_url` 有設定，仍會以 HTTP GET 擷取快照作為備援。

---

## 發布主題（出站）

> **實作狀態**：四個出站主題均已啟用。`home/home_state/presence` 每 60 秒發布；`home/home_state/alarm_decision` 在告警到達後立即發布（wake-on-event），後續每 60 秒重算，90 秒窗口過期後停止；`home/display/status` 在每次 e-Paper 成功更新後發布；`home/home_state/alarm_command` 由 Button 3/4 觸發時發布（任意頁面皆有效）。

本服務發布以下主題，供 **Agent 1** 或其他訂閱者使用：

所有出站訊息自動附加以下欄位：
```json
{
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

---

### `home/home_state/presence` — 占用狀態

每次占用計分更新時發布（約每 60 秒）。

```json
{
  "state": "OCCUPIED",
  "score": 1.0,
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `state` | string | `"OCCUPIED"`, `"UNOCCUPIED"`, 或 `"UNKNOWN"` |
| `score` | float | 目前占用計分（`1.0` = OCCUPIED，`0.0` = UNOCCUPIED）|

---

### `home/home_state/alarm_decision` — 告警決策

由 `_presence_loop()` 計算並發布：收到 `home/security/alert` 時透過 `asyncio.Event` 立即喚醒，後續每 60 秒週期性重算（若告警仍有效）；計算條件為 `state.last_alert` 存在且未超過 90 秒決策窗口；每次計算均記錄至 `alarm_decisions` 資料表。

> **時序**：收到 `home/security/alert` 後，`alarm_decision` 通常在數百毫秒內發布（wake-on-event）；90 秒窗口過期後停止發布，避免對已超時的告警繼續決策。

```json
{
  "alarm_decision": "CANCEL_ALARM",
  "source": "presence_loop",
  "reason": "Known user present during motion",
  "score": 1,
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `alarm_decision` | string | `"TRIGGER_ALARM"`, `"NO_ACTION"`, 或 `"CANCEL_ALARM"` |
| `source` | string | 固定為 `"presence_loop"` |
| `reason` | string | 決策理由描述 |
| `score` | int | 當前占用計分（整數） |

**決策邏輯**：

| 情況 | 決策 |
|------|------|
| 無人（UNOCCUPIED / UNKNOWN）且無已知人臉 | `TRIGGER_ALARM` |
| 有人（OCCUPIED）且有已知人臉 | `CANCEL_ALARM` |
| 其他不確定情況 | `NO_ACTION` |

---

### `home/display/status` — 顯示器狀態

每次 e-Paper 成功寫入後發布。

```json
{
  "status": "updated",
  "page": "dashboard",
  "refresh_type": "fast",
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `page` | string | 本次渲染的頁面類型：`"dashboard"`、`"alert"` 或 `"ap_mode"` |
| `refresh_type` | string | 刷新方式：`"full"`（完整刷新）或 `"fast"`（快速局部刷新）|

---

### `home/home_state/alarm_command` — 按鈕告警指令

由按鈕 3（GPIO 27）或按鈕 4（GPIO 22）觸發，僅在目前頁面為 `alert` 時發送。

```json
{
  "alarm_decision": "TRIGGER_ALARM",
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `alarm_decision` | string | `"TRIGGER_ALARM"`（按鈕 3：重新觸發告警）或 `"CANCEL_ALARM"`（按鈕 4：取消告警）|

**觸發條件**：
- 按鈕 3（TRIGGER_ALARM）：目前頁面為 `alert` 時，每次按下均立即發布 MQTT 並同步播放 `alert.wav`；**無冷卻**，連按會重複通知 Agent 1 並重播警報音；同時更新 `alert_last_triggered_at` 以延長告警頁面逾時計時
- 按鈕 4（CANCEL_ALARM）：目前頁面為 `alert` 時發布；無冷卻保護

> 此主題不切換頁面、不清除 alert state，純粹通知 Agent 1 採取對應行動。

---

## 訊息格式規範

所有訊息遵循以下規範：

1. **編碼**：UTF-8 JSON 字串
2. **必填欄位**：所有訊息必須包含 `agent` 和 `timestamp`
3. **時間格式**：ISO 8601（`2026-05-29T10:30:00` 或帶微秒 `2026-05-29T10:30:00.123456`）
4. **QoS**：出站訊息使用 QoS 1；入站訊息處理為 QoS 0 或 1

---

## 主題摘要

| 方向 | 主題 | 說明 |
|------|------|------|
| 訂閱 | `home/security/door` | 門狀態事件（JSON, QoS 1）|
| 訂閱 | `home/security/face` | 人臉辨識事件（JSON, QoS 1）|
| 訂閱 | `home/security/alert` | 安全告警（立即顯示，JSON, QoS 1）|
| 訂閱 | `home/security/status` | Agent 1 狀態心跳（JSON, QoS 1）|
| 訂閱 | `home/security/camera` | 即時攝影機 JPEG 畫面（raw binary, QoS 0, max 64 KB）|
| 發布 | `home/home_state/presence` | 占用狀態更新 |
| 發布 | `home/home_state/alarm_decision` | 告警決策結果 |
| 發布 | `home/home_state/alarm_command` | 按鈕觸發告警指令（TRIGGER_ALARM / CANCEL_ALARM）|
| 發布 | `home/display/status` | 顯示器狀態回報 |

---

## 測試 MQTT 連線

使用 `mosquitto_pub` / `mosquitto_sub` 手動測試：

```bash
# 訂閱所有 home/# 主題（監聽模式）
mosquitto_sub -h 192.168.1.100 -t "home/#" -v

# 模擬 Agent 1 發送門開事件（先送 closed 再送 open，才能觸發開門天氣提醒）
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/door" \
  -m '{"door_state":"closed","timestamp":"2026-05-29T10:29:00","agent":"test"}'

mosquitto_pub -h 192.168.1.100 \
  -t "home/security/door" \
  -m '{"door_state":"open","timestamp":"2026-05-29T10:30:00","agent":"test"}'

# 模擬已知人臉辨識（FaceGuard 協定，使用 vote_result）
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/face" \
  -m '{"vote_result":"lance","known":true,"timestamp":"2026-05-29T10:30:00","agent":"test"}'

# 模擬安全告警（會立即觸發 e-Paper 更新）
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/alert" \
  -m '{"type":"motion","severity":"high","timestamp":"2026-05-29T10:30:00","agent":"test"}'
```

也可使用 Pi 上的測試腳本：

```bash
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_mqtt'
```
