# MQTT 協定規範

## 連線設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| Broker Host | `192.168.1.100` | 在 `config.yaml` 中設定 |
| Port | `1883` | 標準 MQTT 埠 |
| Client ID | `epaper-home-display` | 識別本服務的客戶端 ID |
| QoS | `1` | 所有發布訊息使用 QoS 1（至少送達一次）|

---

## 訂閱主題（入站）

本服務訂閱以下主題，接收來自 **Agent 1** 的事件：

### `home/security/door` — 門狀態事件

門的開關狀態更新。

```json
{
  "state": "open",
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `state` | string | `"open"` 或 `"closed"` |
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**效果**：
- 更新 `state.last_door_event`
- 寫入 `door_events` 資料表
- 門事件計入占用計分（`door_weight`），有效期 `door_window_seconds`

---

### `home/security/face` — 人臉辨識事件

人臉辨識結果。

```json
{
  "identity": "lance",
  "known": true,
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `identity` | string | 辨識出的身份（已知人員名稱，或 `"unknown"`）|
| `known` | bool | `true` = 已知人員；`false` = 陌生人 |
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**效果**：
- 更新 `state.last_face_event`
- 寫入 `face_events` 資料表
- **已知人臉**（`known: true`）計入占用計分（`face_weight`），有效期 `face_window_seconds`
- 觸發告警決策重新計算

---

### `home/security/alert` — 安全告警事件

觸發立即顯示更新（不等待牆鐘對齊）。

```json
{
  "type": "motion",
  "severity": "high",
  "timestamp": "2026-05-29T10:30:00",
  "agent": "agent-1"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `type` | string | 告警類型，如 `"motion"`, `"unknown-person"` |
| `severity` | string | 嚴重程度（可選） |
| `timestamp` | string | ISO 8601 格式 |
| `agent` | string | 發送方識別碼 |

**效果**：
- 更新 `state.last_alert`
- 立即觸發 `display_queue.put_nowait("alert")`，e-Paper 立即刷新
- Discord 通知（⚠️ 服務已建立但尚未連接至告警流程，目前不會送出）
- 音效提醒（⚠️ 服務已建立但尚未連接至告警流程，目前不會播放）

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

## 發布主題（出站）

> **⚠️ 實作狀態**：以下發布主題為計劃中的 MQTT 介面規格，`MQTTService.publish()` API 已就緒，但目前主服務流程（`app/main.py`）尚未呼叫發布函式。Agent 1 或其他訂閱者**目前不會**收到這些訊息，待後續版本啟用。

本服務計劃發布以下主題，供 **Agent 1** 或其他訂閱者使用：

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
  "score": 2.5,
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `state` | string | `"OCCUPIED"`, `"UNOCCUPIED"`, 或 `"UNKNOWN"` |
| `score` | float | 目前占用計分 |

---

### `home/home_state/alarm_decision` — 告警決策

每次收到安全事件後發布。

```json
{
  "decision": "IGNORE",
  "reason": "Known face detected, occupant present",
  "score": 3.0,
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `decision` | string | `"ALARM"`, `"INVESTIGATE"`, 或 `"IGNORE"` |
| `reason` | string | 決策理由描述 |
| `score` | float | 當前占用計分 |

**決策邏輯**：

| 情況 | 決策 |
|------|------|
| 無人 + 無已知人臉 | ALARM |
| 有人 + 已知人臉 | IGNORE |
| 其他情況 | INVESTIGATE |

---

### `home/display/status` — 顯示器狀態（選用）

e-Paper 更新狀態回報。

```json
{
  "status": "updated",
  "refresh_type": "fast",
  "agent": "epaper-home-display",
  "timestamp": "2026-05-29T10:30:00.123456"
}
```

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
| 訂閱 | `home/security/door` | 門狀態事件 |
| 訂閱 | `home/security/face` | 人臉辨識事件 |
| 訂閱 | `home/security/alert` | 安全告警（立即顯示）|
| 訂閱 | `home/security/status` | Agent 1 狀態心跳 |
| 發布 | `home/home_state/presence` | 占用狀態更新 |
| 發布 | `home/home_state/alarm_decision` | 告警決策結果 |
| 發布 | `home/display/status` | 顯示器狀態回報 |

---

## 測試 MQTT 連線

使用 `mosquitto_pub` / `mosquitto_sub` 手動測試：

```bash
# 訂閱所有 home/# 主題（監聽模式）
mosquitto_sub -h 192.168.1.100 -t "home/#" -v

# 模擬 Agent 1 發送門開事件
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/door" \
  -m '{"state":"open","timestamp":"2026-05-29T10:30:00","agent":"test"}'

# 模擬已知人臉辨識
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/face" \
  -m '{"identity":"lance","known":true,"timestamp":"2026-05-29T10:30:00","agent":"test"}'

# 模擬安全告警（會立即觸發 e-Paper 更新）
mosquitto_pub -h 192.168.1.100 \
  -t "home/security/alert" \
  -m '{"type":"motion","severity":"high","timestamp":"2026-05-29T10:30:00","agent":"test"}'
```

也可使用 Pi 上的測試腳本：

```bash
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_mqtt'
```
