# HydraCup 端整合交接文件

**這份文件的交付對象是 [esp32-hydracup](https://github.com/Ning0612/esp32-hydracup) 專案**，說明該韌體需要新增哪些程式碼才能與 `epaper-display` 完成 MQTT 整合。`esp32-hydracup` 是獨立 repo，本文件不包含該 repo 的程式碼本身。

協議本體（topic、payload schema、QoS、發布時機）定義在 [hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md)，本文件不重複列出，只講「怎麼落地到 HydraCup 現有的程式碼結構」。

> **狀態：已實作。** 本文件原始版本是實作前的落地建議；HydraCup 端完成實作後，下方已依實際落地結果更新，**與最初建議有幾處刻意差異**（函式庫限制、阻塞式 I/O 考量、既有程式碼風格），已在對應段落標註「實際實作」。差異對照與根因分析見 [hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md) 的「QoS 落差說明」。以下 HydraCup 端程式碼細節依實作方回報整理，未逐行核對 esp32-hydracup 原始碼。

## 背景

`epaper-display`（Raspberry Pi e-Paper 儀表板）新增了一張卡片，顯示 HydraCup 的「今日喝水量/目標量/完成比例」。整合前 HydraCup 已有：
- WiFi 連線（`lib/WiFiManager`）
- 本機 REST API（`lib/DashboardServer`，`GET /api/status`、`/api/weight` 等）
- Discord webhook 通知（`lib/DiscordNotifier`，含背景任務、重試/backoff 邏輯）
- 喝水事件偵測狀態機（`lib/DrinkDetector`，`DRINK_CONFIRMED` / `REFILL_DETECTED` 狀態轉換）
- 每日目標值 `dailyGoalMl`（NVS `water_config` namespace，透過 `lib/ConfigManager` 管理，`/api/config` 曝露）

整合前**沒有 MQTT client**。本次整合新增了一個 MQTT publisher 模組（`lib/MqttPublisher`，見下方），讓 HydraCup 在偵測到喝水事件與定期心跳時，把資料推送到 Pi 上的 Mosquitto broker。

## 依賴套件

`platformio.ini` 的 `lib_deps` 新增 `knolleary/PubSubClient`（實際採用；輕量、與現有 `lib_deps` 如 `bogde/HX711`、`bblanchon/ArduinoJson` 風格一致）。

**⚠️ 已知限制（實作階段確認，影響協議 QoS）**：`PubSubClient` 的 OSS 版 `publish()` API **完全沒有 QoS 參數，一律以 QoS 0 發布**，只有 `connect()` 時透過 `willQos` 註冊的 LWT 才能真正指定 QoS。這代表 `hydracup/status` 與上線通知（`{"online":true}`）實際都只能做到 QoS 0，並非原規劃的 QoS 1；只有斷線 LWT（`{"online":false}`）能達到真正的 QoS 1。這是函式庫本身的限制，非實作疏漏，已在協議文件標註為已知、已接受的落差（家用 LAN 環境下影響極小，且 epaper-display 端的心跳逾時判斷本來就能容忍偶發訊息遺失）。若未來想要真正的 QoS 1/2，需改用支援完整 QoS 的函式庫（例如 `256dpi/arduino-mqtt`），屬於後續優化，非本次範圍。

**封包大小**：建議在 `platformio.ini` 的 `build_flags` 加大預設封包上限（`PubSubClient` 預設僅 128–256 bytes，本協議 payload 約 100–150 bytes，理論上夠用但留安全餘裕）：

```ini
build_flags =
  -D MQTT_MAX_PACKET_SIZE=512
```

## 模組：`lib/MqttPublisher`（`MqttPublisher.h`/`.cpp`）

比照現有 `lib/DiscordNotifier` 的獨立模組慣例（`.h`/`.cpp` 配對，自成一個單一職責模組）。

**原始建議** vs **實際實作**：原始建議是簡單介面 `begin(const MqttConfig&)` + 主迴圈直接呼叫 `loop()` 處理重連。實作階段發現 `PubSubClient::connect()`／`.loop()` 是**阻塞式 socket 呼叫**，若直接放在 `src/main.cpp` 的主 `loop()` 裡，broker 離線時會讓整個主迴圈瞬間卡住（秤重採樣、OLED、儀表板 HTTP 全部停擺），違反專案「禁 `delay()`／禁阻塞」的既有非阻塞原則——這是規格書與原始建議都沒考慮到的落地細節，實作階段才發現並改用背景 task 架構：

- 把 `PubSubClient`/`WiFiClient` 的存取整個搬到獨立的 **FreeRTOS 背景 task**（`MqttPublisher::_taskLoop()`）執行，包含連線、重連、`loop()` 心跳、實際 `publish()` 呼叫。
- 主線程（`src/main.cpp` 的主 `loop()`）不直接碰 `PubSubClient`，只透過 `QueueHandle_t` 把「要發布什麼」丟進佇列，`_taskLoop()` 背景消化佇列並執行實際發布，主線程不會被 broker 連線狀況拖慢。
- 對外介面比照專案既有的 `DiscordNotifier`／`TimeManager` 慣例，不新增獨立的 `MqttConfig` struct，直接吃既有的 `AppConfig`：
  ```cpp
  // lib/MqttPublisher/MqttPublisher.h
  class MqttPublisher {
  public:
      void init(AppState& state, const AppConfig& config);   // 建立背景 task、WiFiClient + PubSubClient，設定 LWT
      void publishStatus(uint32_t currentMl, uint32_t goalMl, const char* event);  // 丟進發布佇列，非阻塞
      bool isConnected() const;
  };
  ```
  （原始建議的 `begin(const MqttConfig&)` 只是示意介面，非強制命名；改成 `init(AppState&, const AppConfig&)` 是為了跟既有模組風格一致，屬於非功能性差異。）

**`init()` 內部要做的事**：
- 建立背景 task，task 內用 `WiFiClient` + `PubSubClient` 建立連線物件，設定 broker host/port（取自 `AppConfig` 新增的 `mqttXxx` 欄位，見下方）。
- 若 `username` 非空，呼叫對應的帳密登入 API（`PubSubClient::connect()` 的 overload 支援 `willTopic`/`willQos`/`willRetain`/`willMessage` 參數，一次把 LWT 也設好）：
  ```cpp
  mqttClient.connect(clientId, username, password,
                      "hydracup/availability", 1, true, "{\"online\":false}");
  ```
- 連線成功後立即發布一次 `{"online": true}`（retained）到 `hydracup/availability`，覆蓋上一次的 LWT 離線訊息（見協議文件的「發布時機」表）。

**背景 task（`_taskLoop()`）內部要做的事**：
- 呼叫 `mqttClient.loop()` 維持連線（`PubSubClient` 需要定期呼叫才能處理 keep-alive 與重連）。
- 消化 `publishStatus()` 透過佇列丟進來的發布請求，實際呼叫 `_mqttClient.publish(topic, payload, retained)`。
- 若距離上次發布超過 `mqttHeartbeatSec` 秒，主動排入一次 `publishStatus(currentMl, goalMl, "heartbeat")`。
- 斷線重連建議加入簡單的最小重試間隔（例如至少間隔 5 秒才重試一次 `connect()`），避免 WiFi 不穩時無限快速重試佔用 CPU。

**`publishStatus()` 內部要做的事**：
- 用 `ArduinoJson`（專案已依賴）組裝符合協議規格的 JSON payload（見 [hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md#hydracupstatus) 的欄位表）。
- `pct` 欄位可選擇性帶上（`currentMl / (float)goalMl`，`goalMl` 為 0 時省略此欄位讓 epaper-display 端自行判斷）。
- 發布到 `hydracup/status`，`retain=true`；**QoS 實際為 0**（`PubSubClient::publish()` 無 QoS 參數，見上方「已知限制」），並非原規劃的 `qos=1`。

## 需新增的設定欄位

掛在既有 `AppConfig`（`include/app_types.h`）與 `ConfigManager`（NVS `water_config` namespace），比照現有 `dailyGoalMl` 的持久化方式，並透過既有 `/api/config` REST 端點（GET/POST）與 `data/settings.html` 網頁曝露供使用者設定：

| 欄位 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `mqttEnabled` | bool | `false` | 總開關，關閉時完全不建立 MQTT 連線 |
| `mqttBrokerHost` | string | `""` | Pi 的區網位址或 IP |
| `mqttBrokerPort` | uint16 | `1883` | Broker port |
| `mqttUsername` | string | `""` | Broker 登入帳號 |
| `mqttPassword` | string | `""` | Broker 登入密碼 |
| `mqttClientId` | string | `"hydracup-device"` | 建議含裝置序號以利多裝置除錯 |
| `mqttHeartbeatSec` | uint16 | `60` | 心跳間隔（秒），需與 epaper-display 端的 `heartbeat_timeout_sec`（預設 180 = 心跳的 3 倍）搭配設定，避免誤判過期 |

> **⚠️ 設定生效時機（兩端不對稱，注意操作順序）**：HydraCup 端這些 `mqttXxx` 設定修改後**需要重開機才生效**，比照 WiFi/NTP 等既有設定的慣例，不是即時套用。這與 epaper-display 端的 `PUT /settings/mqtt`（存檔後立即斷線重連、不需重啟，見 [docs/webui.md](webui.md)）行為不對稱——協議本身沒有強制要求兩端一致，但操作時要記得：改了 HydraCup 端的 MQTT 設定要手動重開機才會用新設定連線；改 epaper-display 端則會立刻生效。

## 掛載點（Hook Points）

- **`lib/DrinkDetector`** 狀態機：在 `DRINK_CONFIRMED` 與 `REFILL_DETECTED` 這兩個狀態轉換發生時，呼叫 `mqttPublisher.publishStatus(currentMl, dailyGoalMl, event)`（`event` 對應傳入 `"drink"` 或 `"refill"`）。確切呼叫位置比照現有 `DiscordNotifier` 在相同狀態轉換點的呼叫方式（兩者是同一組事件來源，只是通知管道不同）。`publishStatus()` 本身是非阻塞的（丟進佇列由背景 task 處理，見上方模組說明），可以直接在狀態轉換當下呼叫，不需要額外考慮阻塞風險。
- **`src/main.cpp`** 主迴圈（`loop()` 函式）：新增 `mqttPublisher.init(state, config)` 於啟動階段呼叫一次；主迴圈本身**不需要**呼叫類似 `mqttPublisher.loop()` 的輪詢函式（與原始建議不同），因為連線維護與心跳都已經在 `MqttPublisher` 自己的背景 task 裡處理，`src/main.cpp` 維持只做編排（thin orchestrator）的既有慣例，甚至比原始建議更乾淨。
- **`lib/DisplayManager`**（OLED，選配）：若希望在裝置本機 OLED 上也顯示 MQTT 連線狀態（例如一個小圖示），可參考現有 WiFi 連線狀態圖示的呈現方式；此項為選配，不影響 epaper-display 端功能。

## 測試建議

實作完成後，可用 `mosquitto_sub` 在另一台機器上獨立驗證（不需要 epaper-display 端上線）：

```bash
mosquitto_sub -h <Pi-IP> -p 1883 -u hydracup-device -P <password> -t 'hydracup/#' -v
```

觸發一次真實喝水/加水動作，確認：
1. `hydracup/status` 有收到對應 `event` 的訊息，欄位符合協議 schema。
2. 斷開裝置 WiFi（模擬異常斷線），確認 `hydracup/availability` 在數秒內收到 `{"online": false}`（驗證 LWT 生效）。
3. 重新連線後，`hydracup/availability` 立即收到 `{"online": true}`。
4. 靜置超過 `mqttHeartbeatSec` 秒但不觸發喝水事件，確認仍會收到 `event: "heartbeat"` 的 `hydracup/status`。

完整協議欄位定義與 QoS/retained 規則請見 [hydracup-mqtt-protocol.md](hydracup-mqtt-protocol.md)。
