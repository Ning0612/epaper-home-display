# Bambu Lab MQTT 協議

epaper-display 透過 Bambu Lab 雲端 MQTT broker 讀取印表機列印狀態，並把列印進度顯示在 dashboard 左下角的 Water / Printer 卡片。這條連線由 `app/services/printer_mqtt.py::BambuMQTTService` 負責，與 HydraCup 的 `app/services/mqtt_client.py` 是兩個完全獨立的 MQTT client、兩個不同的 broker。

HydraCup MQTT 連到專案自己在 Raspberry Pi 上架的 Mosquitto broker（`:1883`，無 TLS）；Bambu Lab MQTT 則連到 Bambu 雲端 broker（`us.mqtt.bambulab.com:8883`，TLS 標準憑證驗證）。兩者的 topic、payload、離線判斷與資料合併語義都不同，不應合併描述或共用設定。

## 角色

- **Bambu Lab 雲端 MQTT broker**：BambuMQTTService 的連線目標，固定為 `mqtts://us.mqtt.bambulab.com:8883`。epaper-display 不再直連印表機本機 IP，也不需要印表機開啟 LAN Only Mode。
- **Bambu Lab 印表機**：透過 Bambu 雲端通道提供列印狀態。epaper-display 連線成功後會主動送出一次 `pushall` request，要求回傳完整狀態。
- **epaper-display（Raspberry Pi）**：MQTT client，訂閱印表機 `report` topic，解析 `print` 子物件並更新 `AgentState.printer_*` 欄位，供 dashboard 顯示列印進度。
- **Broker**：Bambu 雲端 broker，而不是 Pi 上的 Mosquitto，也不是印表機 LAN 模式內建 broker。不需要、也不應在 Pi 上另外部署 Bambu 用 broker。

## 連線設定

| 欄位 | 值 |
|------|------|
| Host | 固定常數 `BAMBULAB_CLOUD_MQTT_HOST = "us.mqtt.bambulab.com"`，不由 `config.yaml` 設定。 |
| Port | 固定常數 `BAMBULAB_CLOUD_MQTT_PORT = 8883`，不由 `config.yaml` 設定。 |
| TLS | `client.tls_set()`，使用系統信任的標準憑證驗證；不再呼叫 `tls_insecure_set(True)`，也不跳過憑證驗證。 |
| Username | `u_{uid}`，其中 `uid` 來自 `data/bambu_creds.json`。 |
| Password | `access_token`，來自 `data/bambu_creds.json`。 |
| Client ID | `epaper-bambu-{serial}`。 |
| 停用條件 | `creds_path` 指向的檔案不存在、不是 JSON object、JSON 格式錯誤，或讀不到有效的 `access_token`、`uid`、有效 serial（`printer.serial` 覆蓋值或 credentials 內的 `serial`）任一項時，`BambuMQTTService` 不建立 `mqtt.Client`、不嘗試連線，共記錄兩則 INFO（`_load_credentials()` 一則說明原因，`start()` 因 client 為 `None` 再記一則）。 |

設定 dataclass 定義於 `app/config.py::PrinterConfig`：

```yaml
printer:
  serial: ""
  creds_path: "data/bambu_creds.json"
```

`serial` 是可選覆蓋值：若 `config.yaml` 的 `printer.serial` 有填值，會覆蓋 credentials 檔案裡的 `serial`，適合多台印表機或手動指定情境；若留空，則使用 `tools/bambu_auth.py` 寫入 `data/bambu_creds.json` 的 `serial`。

`config.example.yaml` 採用與 `claude_usage.creds_path`、`codex_usage.creds_path` 類似的 token 檔案設定風格。WebUI 的 `/settings` 頁面「Bambu 印表機設定」區塊只提供 `serial` 一個可編輯欄位；帳號登入、token 取得與 credentials 檔案建立需在筆電執行 `tools/bambu_auth.py` 完成。

## 認證與 credentials 檔案

`tools/bambu_auth.py` 是互動式命令列工具，預期在筆電執行一次，完成後把 `data/bambu_creds.json` 複製到 Pi：

```bash
./.venv/Scripts/python.exe tools/bambu_auth.py
scp data/bambu_creds.json pi@epaper-display.local:~/epaper-home-display/data/
```

工具流程如下：

1. 詢問 Bambu Lab email 與密碼；密碼使用 `getpass`，不會明文顯示。
2. 呼叫 `POST https://api.bambulab.com/v1/user-service/user/login`，body 為 `{"account": email, "password": password}`。
3. 若回應 `loginType` 是 `verifyCode`，提示使用者到信箱取得驗證碼，再以 `{"account": email, "code": verification_code}` 呼叫同一個 login endpoint。
4. 成功後讀取 `accessToken`。
5. 呼叫 `GET https://api.bambulab.com/v1/design-user-service/my/preference`，帶 `Authorization: Bearer {accessToken}`，讀取 `uid`。
6. 呼叫 `GET https://api.bambulab.com/v1/iot-service/api/user/bind`，同樣帶 Authorization header，讀取裝置清單並用 `dev_id` 自動挑選或讓使用者選擇印表機序號；若裝置 API 失敗，改要求手動輸入序號。
7. 將 `access_token`、`uid`、`serial` 寫入 `data/bambu_creds.json`，並嘗試把檔案權限設為只有擁有者可讀寫。

credentials 檔案格式：

```json
{
  "access_token": "...",
  "uid": "...",
  "serial": "..."
}
```

注意：上述 Bambu REST API endpoint、欄位名稱與 token 行為來自社群逆向工程文件 [Doridian/OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI)，不是 Bambu 官方公開文件，也尚未視為官方保證的穩定 API。若 Bambu 變更雲端 API，`tools/bambu_auth.py` 可能需要更新。

目前文件與程式都不描述自動 refresh 流程。token 有效期約 3 個月（社群文件常見 `expiresIn: 7776000` 秒），社群文件也記載 refresh token 機制不可靠、常回 401；本專案沒有實作自動 refresh。token 過期後，重新執行 `tools/bambu_auth.py`，再重新 `scp data/bambu_creds.json` 到 Pi。

## Topics

| Topic | 方向 | 訂閱 QoS | 發布 QoS | Retained | 說明 |
|-------|------|---------|---------|----------|------|
| `device/{serial}/report` | Bambu 雲端/印表機 → epaper-display | 0 | 依 Bambu 實作 | 否 | 印表機狀態推送。epaper-display 只解析 payload 中的 `print` 子物件。 |
| `device/{serial}/request` | epaper-display → Bambu 雲端/印表機 | - | 0 | 否 | epaper-display 連線成功後發布 `pushall` request，要求一次完整狀態。 |

Bambu report 預設不應假設像 HydraCup retained status 那樣，在 subscriber 連上 broker 後自動補一包完整 retained 訊息。因此 `BambuMQTTService._on_connect()` 在訂閱 `device/{serial}/report` 後，會主動發布一次 `pushall` request。後續收到的 report 可能是增量更新，不能把缺少的欄位解讀為清空。

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

| 欄位 | 型別 / 驗證 | 必填 | 說明 |
|------|-------------|------|------|
| `mc_percent` | int/float，`0.0` 到 `100.0`，不接受 bool、NaN、Infinity | 否 | 轉成 `PrintStatus.pct` 的 `0.0` 到 `1.0` 浮點數；無效或缺少時回傳 `None`。 |
| `mc_remaining_time` | int，或整數值 float，`0` 到 `10080`，不接受 bool | 否 | 轉成 `PrintStatus.remaining_min`；單位是分鐘。無效或缺少時回傳 `None`。 |
| `subtask_name` | string，trim 後不可空白且長度不超過 100 | 否 | 優先轉成 `PrintStatus.task_name`；無效或缺少時 fallback 到 `gcode_file`。 |
| `gcode_file` | string，trim 後不可空白且長度不超過 100 | 否 | `subtask_name` 無效或缺少時的 fallback。 |
| `gcode_state` | string，trim 後轉大寫，需符合 `^[A-Za-z_]{1,32}$` | 否 | 轉成 `PrintStatus.gcode_state`；例如 `RUNNING`、`PAUSE`。無效或缺少時回傳 `None`。 |

**epaper-display 解析語義**（`app/logic/printer.py::parse_print_status()`）：

- Bambu report 採用逐欄位獨立驗證、per-field 合併語義。
- `PrintStatus` 固定包含 4 個可能為空的欄位：`pct`、`remaining_min`、`task_name`、`gcode_state`。
- 任一欄位缺少或驗證失敗時，該欄位回傳 `None`，不代表整包訊息失敗。
- `app/services/printer_mqtt.py::_handle_report()` 只把非 `None` 欄位寫入 `state.printer_*`；`None` 欄位會保留前一次已知值。

這點刻意不同於 HydraCup 的 `app/logic/hydration.py::parse_status()`：HydraCup status 的核心欄位是單包完整狀態，任一必填欄位無效就整包丟棄；Bambu report 則可能是增量推送，所以必須逐欄位合併，避免某次增量訊息缺少 `task_name` 或 `remaining_time` 時把畫面上的既有資料清掉。

## `device/{serial}/request`

epaper-display 連線成功後會發布一包：

```json
{
  "pushing": {
    "sequence_id": "0",
    "command": "pushall"
  }
}
```

這個 request 用來要求 Bambu 回傳一次完整狀態。它不是 retained 訊息，也不是週期性 heartbeat；目前只在 MQTT connect 成功後送出。

## 訊息流程

| 事件 | 觸發動作 | Topic |
|------|---------|-------|
| MQTT 連線成功 | `BambuMQTTService._on_connect()` 訂閱 report 後立即發布 `pushall` | `device/{serial}/request` |
| 印表機狀態更新 | Bambu 雲端/印表機推送 | `device/{serial}/report` |

epaper-display 收到 `report` 後在 paho-mqtt 的背景執行緒解析 JSON，並用 `asyncio.run_coroutine_threadsafe()` 把 `_handle_report()` 派回主 event loop 更新 `state`。這個 threading / event-loop 邊界與 HydraCup MQTT service 類似，但 broker、topic、payload 與資料語義不同。

## 離線 / 狀態判斷規則

Bambu 印表機的離線判斷只看 MQTT broker 連線狀態：

- connect 成功：`state.printer_broker_connected = True`
- connect 失敗或 disconnect callback：`state.printer_broker_connected = False`
- service stop 或 credentials 無效停用：`state.printer_broker_connected = False`

目前沒有像 HydraCup 的 `mqtt.heartbeat_timeout_sec` 逾時機制。`state.printer_updated_at` 只表示最近一次成功處理 `print` report 的時間，不用來判定離線。

Dashboard 左下角的列印狀態是否顯示為 active，邏輯位於 `app/display/renderer_cards.py::_draw_card_water_printer()`：

```python
state.printer_broker_connected and state.printer_gcode_state in {"RUNNING", "PAUSE"}
```

若 broker 未連線或 `gcode_state` 不是上述狀態，畫面顯示 `No active print`；百分比顯示 `--%`，剩餘時間顯示 `--`，並使用 muted 視覺狀態。

剩餘時間格式由 `app/logic/printer.py::format_remaining()` 產生：

| 輸入 | 輸出 |
|------|------|
| `83` | `1h23m` |
| `60` | `1h00m` |
| `45` | `45m` |
| `0` | `0m` |
| `None` 或負數 | `--` |

## Broker 部署與本地設定

Bambu Lab 這邊沒有 Pi 端 broker 部署步驟。broker 是 Bambu 雲端服務：

- 連線目標固定為 `us.mqtt.bambulab.com:8883`。
- 不需要設定印表機 IP、port 或 access code。
- 不需要開啟 LAN Only Mode；Bambu App 與雲端功能不會因本專案設定而停用。
- 先在筆電執行 `tools/bambu_auth.py` 產生 `data/bambu_creds.json`，再複製到 Pi 專案的 `data/` 目錄。
- `config.yaml` 的 `printer.serial` 只用於覆蓋 credentials 檔案內的 `serial`；一般單台印表機可留空。
- 不要把 Bambu 設定填到 `mqtt.*`；`mqtt.*` 是 HydraCup 連到 Pi Mosquitto broker 的設定。

## 測試指令

以下指令假設已安裝 `mosquitto-clients`（版本 2.0+），並以 `<uid>`、`<access_token>`、`<serial>` 代替 `data/bambu_creds.json` 內的實際值。Bambu 雲端 MQTT 使用標準受信任 TLS 憑證，範例不需要 `--insecure`；為避免不同版本的預設行為差異造成誤解，範例明確帶上 `--tls-use-os-certs`（使用系統信任的憑證鏈）：

```bash
# 訂閱印表機 report
mosquitto_sub -h us.mqtt.bambulab.com -p 8883 --tls-use-os-certs \
  -u "u_<uid>" -P "<access_token>" \
  -t "device/<serial>/report" -v

# 主動要求一次完整狀態
mosquitto_pub -h us.mqtt.bambulab.com -p 8883 --tls-use-os-certs \
  -u "u_<uid>" -P "<access_token>" \
  -t "device/<serial>/request" \
  -m '{"pushing":{"sequence_id":"0","command":"pushall"}}'
```

也可以從 WebUI 的 `GET /state` 檢查 `printer_*` 欄位是否更新；從 `/settings` 的「Bambu 印表機設定」區塊檢查連線狀態、目前 `gcode_state` 與最後更新時間。

## epaper-display 狀態欄位對照

| MQTT 資料 | 更新到 `AgentState` 欄位（`app/state.py`） |
|-----------|-------------------------------------------|
| `print.mc_percent` | `printer_pct` |
| `print.mc_remaining_time` | `printer_remaining_min` |
| `print.subtask_name`（fallback `print.gcode_file`） | `printer_task_name` |
| `print.gcode_state` | `printer_gcode_state` |
| 成功處理 `print` report | `printer_updated_at` |
| MQTT client connect/disconnect | `printer_broker_connected` |

這些欄位也會由 `GET /state` 回傳，供 WebUI 與除錯使用。`GET /settings/config` 會回傳 `printer.serial` 與 `printer.creds_path` 設定值，但不會讀取或回傳 Bambu access token、uid 或 credentials 檔案內容。

## 目前不解析的資料

目前 MVP 只顯示列印百分比、剩餘時間、任務名稱與 `gcode_state`。尚未解析 AMS、溫度、風扇、錯誤碼、列印速度等其他欄位。若未來要擴充 `PrintStatus` dataclass，仍應維持 per-field 合併語義，避免增量 report 缺少欄位時清掉既有狀態。
