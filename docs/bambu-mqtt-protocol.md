# Bambu Lab MQTT 協議

epaper-display 透過 Bambu Lab 印表機 LAN 模式內建的本地 MQTT broker 讀取列印狀態，並把列印進度顯示在 dashboard 左下角的 Water / Printer 卡片。這條連線由 `app/services/printer_mqtt.py::BambuMQTTService` 負責，與 HydraCup 的 `app/services/mqtt_client.py` 是兩個完全獨立的 MQTT client、兩個不同的 broker。

HydraCup MQTT 連到專案自己在 Raspberry Pi 上架的 Mosquitto broker（`:1883`，無 TLS）；Bambu Lab MQTT 則直接連到印表機內建 broker（`:8883`，TLS，自簽憑證）。兩者的 topic、payload、離線判斷與資料合併語義都不同，不應合併描述或共用設定。

## 角色

- **Bambu Lab 印表機**：內建 LAN MQTT broker，同時是列印狀態的 publisher。epaper-display 連線成功後會主動送出一次 `pushall` request，要求印表機回傳完整狀態。
- **epaper-display（Raspberry Pi）**：MQTT client，訂閱印表機的 `report` topic，解析 `print` 子物件後更新 `AgentState.printer_*` 欄位，並在 dashboard 顯示列印進度。
- **Broker**：印表機本機內建 broker，位於 `mqtts://<印表機IP>:8883`。不需要、也不應在 Pi 上另外部署 Bambu 用 broker。

## 連線設定

| 欄位 | 值 |
|------|------|
| Host | 印表機 IP，對應 `config.yaml` 的 `printer.host`。留空表示停用 Bambu 整合。 |
| Port | `8883`，對應 `printer.port`。這是 Bambu LAN 模式 MQTT broker 的 TLS port。 |
| TLS | 啟用 TLS，但不驗證憑證：`cert_reqs=ssl.CERT_NONE` 並呼叫 `tls_insecure_set(True)`。Bambu LAN 模式使用自簽憑證，因此目前實作會跳過憑證驗證。 |
| Username | 固定 `bblp`。 |
| Password | 印表機 access code，對應 `printer.access_code`。 |
| Client ID | `epaper-bambu-{serial}`。 |
| 停用條件 | `printer.host`、`printer.serial`、`printer.access_code` 任一留空時，`BambuMQTTService` 不建立 `mqtt.Client`、不嘗試連線，只記錄一則 INFO。 |

設定 dataclass 定義在 `app/config.py::PrinterConfig`：

```yaml
printer:
  host: ""
  port: 8883
  serial: ""
  access_code: ""
```

`config.example.yaml` 只提供空字串佔位值，沒有真實憑證。WebUI 的 `/settings` 頁面也提供「Bambu 印表機設定」區塊；`GET /settings/config` 只回傳 `printer.access_code_set` 布林值，不回傳 access code 明碼。

## Topics

| Topic | 方向 | 訂閱 QoS | 發布 QoS | Retained | 說明 |
|-------|------|---------|---------|----------|------|
| `device/{serial}/report` | Bambu 印表機 → epaper-display | 0 | 依印表機實作 | 否 | 印表機狀態推送。epaper-display 只解析 payload 中的 `print` 子物件。 |
| `device/{serial}/request` | epaper-display → Bambu 印表機 | - | 0 | 否 | epaper-display 連線成功後發布 `pushall` request，要求一次完整狀態。 |

Bambu 印表機預設不會像 HydraCup retained status 那樣，在 subscriber 連上 broker 後自動補一包完整 retained 訊息。因此 `BambuMQTTService._on_connect()` 在訂閱 `device/{serial}/report` 後，會主動發布一次 `pushall` request。後續收到的 report 可能是增量更新，不能把缺少的欄位解讀為清空。

## `device/{serial}/report`

Payload（JSON）範例：

```json
{
  "print": {
    "mc_percent": 42,
    "mc_remaining_time": 83,
    "subtask_name": "benchy_v2.3mf",
    "gcode_file": "benchy_v2.3mf",
    "gcode_state": "RUNNING"
  }
}
```

epaper-display 只讀取 `print` 子物件，並交給 `app/logic/printer.py::parse_print_status(print_obj: dict) -> PrintStatus | None`。若 payload 不是 JSON object、沒有 `print` 子物件，或 `print` 不是 object，會忽略該訊息。

| 欄位 | 型別 / 範圍 | 必填 | 說明 |
|------|-------------|------|------|
| `mc_percent` | int/float，`0.0`～`100.0`，不可為 bool、NaN、Infinity | 否 | 正規化成 `PrintStatus.pct` 的 `0.0`～`1.0` 分數。缺值或無效時該欄位回傳 `None`。 |
| `mc_remaining_time` | int，或整數值 float，`0`～`10080`，不可為 bool | 否 | 對應 `PrintStatus.remaining_min`，單位為分鐘。上限 `10080` 分鐘。缺值或無效時該欄位回傳 `None`。 |
| `subtask_name` | string，trim 後非空，長度不超過 100 | 否 | 優先作為 `PrintStatus.task_name`。缺值或無效時 fallback 到 `gcode_file`。 |
| `gcode_file` | string，trim 後非空，長度不超過 100 | 否 | `subtask_name` 無效時的檔名 fallback。 |
| `gcode_state` | string，trim 後轉大寫，需符合 `^[A-Za-z_]{1,32}$` | 否 | 對應 `PrintStatus.gcode_state`，例如 `RUNNING`、`PAUSE`。缺值或無效時該欄位回傳 `None`。 |

**epaper-display 解析語義**（`app/logic/printer.py::parse_print_status()`）：

- Bambu report 採用逐欄位獨立驗證、per-field 合併語義。
- `PrintStatus` 固定包含 4 個欄位：`pct`、`remaining_min`、`task_name`、`gcode_state`。
- 任一欄位缺值或無效時，只讓該欄位成為 `None`，不影響其他欄位。
- `app/services/printer_mqtt.py::_handle_report()` 只把非 `None` 欄位寫入 `state.printer_*`；`None` 欄位會保留原值，不會清空。

這點刻意不同於 HydraCup 的 `app/logic/hydration.py::parse_status()`：HydraCup status 的核心欄位是單包完整狀態，任一必填欄位無效就整包丟棄；Bambu report 則可能是增量推送，所以必須逐欄位合併，避免某次增量訊息缺少 `task_name` 或 `remaining_time` 時把畫面上的既有資料清掉。

## `device/{serial}/request`

epaper-display 連線成功後會發布一次：

```json
{
  "pushing": {
    "sequence_id": "0",
    "command": "pushall"
  }
}
```

這個 request 用來向印表機要求一次完整狀態。它不是 retained 訊息，也不是週期性 heartbeat；目前實作只在 MQTT connect 成功時送出。

## 發布時機

| 時機 | 觸發來源 | Topic |
|------|---------|-------|
| MQTT 連線成功 | `BambuMQTTService._on_connect()` 訂閱 report 後立即發布 `pushall` | `device/{serial}/request` |
| 印表機狀態更新 | Bambu Lab 印表機 LAN MQTT 推送 | `device/{serial}/report` |

epaper-display 收到 `report` 後透過 paho-mqtt 背景執行緒解析 JSON，再用 `asyncio.run_coroutine_threadsafe()` 將 `_handle_report()` 派回主 event loop 更新 `state`。這個 threading / event-loop 模式與 HydraCup MQTT service 類似，但 broker、topic、payload 與合併語義不同。

## 離線 / 過期判斷規則

Bambu 印表機的離線判斷只看 MQTT broker 連線狀態：

- 連線成功：`state.printer_broker_connected = True`
- connect 失敗或 disconnect callback：`state.printer_broker_connected = False`
- service stop 或設定停用：`state.printer_broker_connected = False`

目前沒有像 HydraCup 的 `mqtt.heartbeat_timeout_sec` 逾時機制。原因是 Bambu LAN MQTT 連線異常時，TCP/TLS socket 會直接斷線，實作上不需要額外的 heartbeat timeout。`state.printer_updated_at` 只表示最近一次成功處理 `print` report 的時間，不用來判定離線。

Dashboard 卡片的「印表機使用中」條件定義在 `app/display/renderer_cards.py::_draw_card_water_printer()`：

```python
state.printer_broker_connected and state.printer_gcode_state in {"RUNNING", "PAUSE"}
```

只有使用中時才顯示列印百分比與剩餘時間；否則檔名顯示 `No active print`，百分比顯示 `--%`，剩餘時間顯示 `--`，整段使用 muted 灰階樣式。

剩餘時間格式由 `app/logic/printer.py::format_remaining()` 產生：

| 輸入 | 輸出 |
|------|------|
| `83` | `1h23m` |
| `60` | `1h00m` |
| `45` | `45m` |
| `0` | `0m` |
| `None` 或負數 | `--` |

## Broker 端部署或連線需求

Bambu Lab 這邊沒有 Pi 端 broker 部署步驟。broker 是印表機 LAN 模式內建服務：

- 確認印表機與 epaper-display 在同一個可互通 LAN。
- 確認印表機 LAN 模式與 access code 可用。
- 在 `config.yaml` 或 WebUI 設定 `printer.host`、`printer.serial`、`printer.access_code`。
- 不要把 Bambu 設定填到 `mqtt.*`；`mqtt.*` 是 HydraCup 連到 Pi Mosquitto broker 的設定。

## 測試指令

以下指令假設已安裝 `mosquitto-clients`，並以 `<printer_ip>`、`<serial>`、`<access_code>` 代替實際值。Bambu LAN broker 使用 TLS 自簽憑證，因此範例使用 `--insecure` 跳過憑證驗證，不需要提供憑證檔案。

```bash
# 監看印表機 report
mosquitto_sub -h <printer_ip> -p 8883 --insecure -u bblp -P <access_code> \
  -t 'device/<serial>/report' -v

# 主動要求一次完整狀態
mosquitto_pub -h <printer_ip> -p 8883 --insecure -u bblp -P <access_code> \
  -t 'device/<serial>/request' \
  -m '{"pushing":{"sequence_id":"0","command":"pushall"}}'
```

也可以從 WebUI 的 `GET /state` 檢查 `printer_*` 欄位是否更新；從 `/settings` 的「Bambu 印表機設定」區塊檢查 broker 連線狀態、目前 `gcode_state` 與最後更新時間。

## epaper-display 狀態欄位對照

| MQTT 資料 | 更新到 `AgentState` 欄位（`app/state.py`） |
|-----------|-------------------------------------------|
| `print.mc_percent` | `printer_pct` |
| `print.mc_remaining_time` | `printer_remaining_min` |
| `print.subtask_name`，fallback `print.gcode_file` | `printer_task_name` |
| `print.gcode_state` | `printer_gcode_state` |
| 成功處理 `print` report | `printer_updated_at` |
| MQTT client connect/disconnect | `printer_broker_connected` |

這些欄位也會由 `GET /state` 回傳，供 WebUI 與除錯使用。`GET /settings/config` 則只暴露 `printer.access_code_set`，不回傳 access code 明碼。

## 目前未實作範圍

目前 MVP 只顯示列印進度、剩餘時間、列印檔名與 `gcode_state`。尚未實作 AMS 多色料架資料、噴嘴/熱床溫度、目前層數/總層數。`PrintStatus` dataclass 與 per-field 合併語義保留了未來擴充空間，但目前程式碼沒有相關欄位或顯示邏輯。
