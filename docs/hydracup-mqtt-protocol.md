# HydraCup MQTT 協議

epaper-display 與 [esp32-hydracup](https://github.com/Ning0612/esp32-hydracup)（ESP32 智慧水杯）之間的 MQTT 通訊協議規格。本文件是雙方共用的唯一事實來源（single source of truth）——`epaper-display` 端的訂閱實作見 `app/services/mqtt_client.py`；`esp32-hydracup` 端的發布實作規劃見 [hydracup-integration-handoff.md](hydracup-integration-handoff.md)。

## 角色

- **HydraCup（ESP32）**：MQTT publisher。偵測到喝水/加水事件時發布，並定期送出心跳。
- **epaper-display（Raspberry Pi）**：MQTT subscriber。訂閱資料後更新 dashboard 上的 Water 卡片。
- **Broker**：Mosquitto，執行於 Raspberry Pi（`epaper-display.local:1883`）。`allow_anonymous false`，雙方都必須以帳號密碼登入。

## 連線設定

| 項目 | 值 |
|------|------|
| Host | Pi 的區網位址（例如 `epaper-display.local` 或其區網 IP） |
| Port | `1883`（無 TLS；區網環境） |
| 認證 | 帳號密碼（broker 設定 `allow_anonymous false`），需先用 `mosquitto_passwd` 建立帳號，見下方「Broker 端部署」 |
| Client ID | 建議 epaper-display 用 `epaper-home-display`，HydraCup 用 `hydracup-device`（或含裝置序號，避免多裝置衝突） |

## Topics

| Topic | 方向 | QoS | Retained | 說明 |
|-------|------|-----|----------|------|
| `hydracup/status` | HydraCup → epaper-display | 1 | 是 | 喝水資料本體 |
| `hydracup/availability` | HydraCup → epaper-display | 1 | 是 | 裝置線上/離線狀態（LWT） |

Retained 訊息的用意：epaper-display 服務重啟後，broker 會立即重送最後一筆訊息，不需要等待下一次事件或心跳。

### `hydracup/status`

Payload（JSON）：

```json
{
  "current_ml": 1200,
  "goal_ml": 2000,
  "pct": 0.6,
  "event": "drink",
  "device_time": "2026-07-02T14:32:10+08:00"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `current_ml` | int，0–9999 | 是 | 今日目前喝水量（毫升）。負數、超出上限、非有限數值一律視為無效 payload（整筆捨棄）。 |
| `goal_ml` | int，0–9999 | 是 | 今日目標飲水量（毫升）。規則同 `current_ml`。 |
| `pct` | float，建議 0.0–1.0 | 否 | 完成比例。缺失時 epaper-display 端會用 `current_ml / goal_ml` 自動計算；若 `goal_ml` 為 0 則視為無法計算（顯示 `--%`）。超出 `-10.0`〜`10.0`（即 -1000%〜1000%）視為無效值，同樣 fallback 為自動計算。 |
| `event` | string | 否 | `"drink"` / `"refill"` / `"heartbeat"` 之一，僅供除錯與未來擴充使用，epaper-display 目前不依賴此欄位做顯示邏輯。 |
| `device_time` | ISO8601 字串 | 否 | HydraCup 裝置端時間戳，僅供除錯參考；epaper-display 顯示的「資料是否過期」判斷用的是**自己收到訊息的時間**，不是這個欄位。 |

**epaper-display 端解析規則**（`app/logic/hydration.py::parse_status()`）：
- `current_ml` / `goal_ml` 缺失、型別錯誤（含 bool）、負數、超過 9999、非有限浮點數（NaN/Infinity）→ 整筆 payload 視為無效，記錄 warning log 並捨棄，不更新既有畫面資料。
- `pct` 缺失或超出合理範圍 → fallback 用 `current_ml / goal_ml` 計算（`goal_ml <= 0` 時無法計算，顯示 `--%`）。

### `hydracup/availability`

Payload（JSON）：

```json
{"online": true}
```

或斷線時：

```json
{"online": false}
```

離線訊息建議透過 MQTT **LWT（Last Will and Testament）** 機制設定：HydraCup 連線時向 broker 註冊 `will_set("hydracup/availability", '{"online": false}', qos=1, retain=true)`，若裝置異常斷線（斷電、WiFi 掉線、未正常呼叫 disconnect），broker 會自動代發此訊息，epaper-display 不需要額外的逾時偵測就能得知裝置離線。

正常上線時，HydraCup 應在 `connect()` 成功後主動發布一次 `{"online": true}`（retained）覆蓋上一次的 LWT 離線訊息。

## 發布時機

| 時機 | 觸發條件 | Topic |
|------|---------|-------|
| 事件觸發 | `DrinkDetector` 進入 `DRINK_CONFIRMED` 或 `REFILL_DETECTED` 狀態 | `hydracup/status`（`event` 設為對應值） |
| 定期心跳 | 每 `mqttHeartbeatSec`（建議預設 60 秒）| `hydracup/status`（`event: "heartbeat"`） |
| 上線通知 | MQTT 連線成功後立即發一次 | `hydracup/availability`（`{"online": true}`） |
| 離線通知 | 異常斷線（LWT 自動觸發）或正常關機前主動發送 | `hydracup/availability`（`{"online": false}`） |

## epaper-display 端的過期判斷

epaper-display 不主動輪詢，而是被動等待訊息。為了避免長時間沒有心跳時仍把舊資料當作「即時」顯示，dashboard 的 Water 卡片會在以下情況改用灰階樣式（而非清空數值）：

- 距離上次收到 `hydracup/status` 的時間超過 `settings.mqtt.heartbeat_timeout_sec`（預設 180 秒，建議設為心跳間隔的 3 倍）。
- `hydracup/availability` 回報 `online: false`。
- 從未收到過任何 `hydracup/status`（`current_ml` 為 `None`）。

對應設定：`config.yaml` 的 `mqtt.heartbeat_timeout_sec`，實作見 `app/display/renderer_cards.py::_draw_card_hydra()`。

## Broker 端部署（Pi 上手動執行）

Pi 上已有 Mosquitto 2.0.21 broker（`systemctl status mosquitto`），設定 `allow_anonymous false`，需要為 epaper-display 訂閱端與 HydraCup 發布端各自建立一組帳密：

```bash
ssh pi@epaper-display.local
sudo mosquitto_passwd -b /etc/mosquitto/passwd epaper-home-display <password>
sudo mosquitto_passwd -b /etc/mosquitto/passwd hydracup-device <password>
sudo systemctl restart mosquitto
```

## 測試指令

在任一台可連到 broker 的機器上（需先安裝 `mosquitto-clients`）：

```bash
# 訂閱所有 hydracup topic，觀察實際訊息
mosquitto_sub -h epaper-display.local -p 1883 -u <username> -P <password> -t 'hydracup/#' -v

# 手動發布一筆測試資料，驗證 epaper-display 端能否正確更新
mosquitto_pub -h epaper-display.local -p 1883 -u <username> -P <password> \
  -t 'hydracup/status' -q 1 -r \
  -m '{"current_ml": 1200, "goal_ml": 2000, "pct": 0.6, "event": "drink"}'

# 標記裝置上線
mosquitto_pub -h epaper-display.local -p 1883 -u <username> -P <password> \
  -t 'hydracup/availability' -q 1 -r -m '{"online": true}'
```

發布後可透過 `GET /state`（epaper-display WebUI，需登入）確認 `hydra_*` 欄位是否更新，或直接等待下一次 dashboard 刷新查看 Water 卡片。

## epaper-display 端狀態欄位對照

| MQTT 事件 | 更新的 `AgentState` 欄位（`app/state.py`）|
|-----------|-------------------------------------------|
| 收到有效 `hydracup/status` | `hydra_current_ml`, `hydra_goal_ml`, `hydra_pct`, `hydra_updated_at` |
| 收到 `hydracup/availability` | `hydra_device_online` |
| MQTT client 連線成功/失敗/斷線 | `hydra_broker_connected` |

這些欄位同時透過 `GET /state` 端點曝露（`app/webui/routes/read_only.py`），方便除錯確認資料是否正確送達。
