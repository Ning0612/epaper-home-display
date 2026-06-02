# ePaper Home Display

以 Raspberry Pi Zero 2W 驅動 Waveshare 7.3" 六色 e-Paper 顯示器（epd7in3e）的智慧家庭狀態面板，整合溫濕度、光線感測、安全偵測與天氣資訊，並與 Agent 1 透過 MQTT 協同工作。

## 畫面預覽

### 儀表板（Dashboard）

![儀表板預覽](docs/images/preview_dashboard.png)

主畫面，每分鐘自動更新。左側顯示日期時間、天氣（即時 + 4 天預報）；右下角為室內溫濕度、Agent 1 安全狀態、Claude / Codex AI 使用量進度條（附重置時間）；右側為圖片輪播區。

### 安全告警（Alert）

![告警頁預覽](docs/images/preview_alert.png)

收到 `home/security/alert` 時立即切換至此頁面，顯示攝影機即時快照（若已設定 `outdoor_agent.snapshot_url`）、門狀態、最後辨識人臉與告警訊息。超過 `alert_page_timeout_sec`（預設 120 秒）後自動返回儀表板。

### WiFi 設定模式（AP Mode）

![AP 模式預覽](docs/images/preview_apmode.png)

Pi 無法連上 WiFi 時自動顯示此頁，引導用戶直接連接 SSID 並透過捕獲入口網站（`http://10.42.0.1:8000/wifi`）完成設定。完成後自動切回儀表板。

> 預覽圖由 `scripts/preview_render.py` 以 mock 資料生成，輸出至 `docs/images/`。

---

## 功能特色

- **天氣面板**：即時天氣 + 5 天預報（OpenWeatherMap），含天氣圖示與溫度
- **室內環境**：DHT22 溫濕度 + 光線感測器（MCP3008 ADC）
- **家庭占用偵測**：純光線感測，燈亮 → OCCUPIED，燈暗 → UNOCCUPIED
- **安全整合**：接收 Agent 1 的門鈴、人臉、告警 MQTT 事件，輸出 ALARM / INVESTIGATE / IGNORE 決策
- **AI 使用量顯示**：直接透過 OAuth 向 Anthropic 與 OpenAI API 輪詢 Claude / Codex 5h 及 7d 使用量，顯示於 e-Paper 面板底部
- **圖片輪播**：上傳自訂圖片，支援裁切、旋轉、翻轉、Floyd-Steinberg dithering，顯示於 e-Paper 面板
- **桌面工作時段**：自動追蹤在場時段、記錄每日統計、離場時推送 Discord 摘要
- **WebUI 設定介面**：密碼保護的瀏覽器設定介面，支援互動地圖選點、MQTT 設定、圖片管理
- **Discord 通知**：裝置上線、桌面時段結束、每日統計推送
- **音效提醒**：天氣提醒播報（aplay + USB 音箱）
- **事件日誌**：SQLite 記錄環境、門、人臉、告警、圖片、工作時段、通知等事件（AI 使用量僅快取於記憶體，不持久化）

---

## 硬體需求

| 元件 | 型號 | 說明 |
|------|------|------|
| 單板電腦 | Raspberry Pi Zero 2W | 運行主服務 |
| 顯示器 | Waveshare 7.3" e-Paper (E) | 800×480，六色（黑、白、紅、黃、藍、綠）|
| 溫濕度感測器 | DHT22 | GPIO 4（BCM） |
| 光線感測器 | 光敏電阻 + MCP3008 ADC | SPI CE1（GPIO 7） |
| 按鈕 | 任意常開按鈕 | GPIO 27（BCM） |
| 音效輸出 | USB 音箱 / USB 喇叭 | micro USB OTG 轉接 |

---

## 快速開始

### 1. 筆電（開發 / 單元測試）

```bash
git clone https://github.com/Ning0612/epaper-home-display.git
cd epaper-home-display
python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
.venv/bin/pip install -r requirements.txt

# 執行所有單元測試（mock 硬體，不需要 Pi）
pytest
```

### 2. Raspberry Pi（部署）

```bash
# Pi 上 clone 並安裝
git clone https://github.com/Ning0612/epaper-home-display.git ~/epaper-home-display
cd ~/epaper-home-display
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install adafruit-circuitpython-dht spidev RPi.GPIO gpiozero

# 複製設定檔並填入必要金鑰
cp config.example.yaml config.yaml
nano config.yaml   # 至少填入 mqtt.broker_host 和 weather.api_key

# 安裝並啟動 systemd 服務
sudo cp systemd/epaper-home-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now epaper-home-display

# 確認服務狀態
systemctl status epaper-home-display --no-pager
journalctl -u epaper-home-display -n 50 --no-pager
```

WebUI 設定介面：`http://<Pi_IP>:8000/settings`

**（選用）啟用 AI 使用量顯示**：在筆電執行 OAuth 授權工具，再將憑證 scp 到 Pi：

```bash
# 在筆電執行
python tools/claude_auth.py   # 產生 data/claude_creds.json
python tools/codex_auth.py    # 產生 data/codex_creds.json

# 複製到 Pi
scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
scp data/codex_creds.json  pi@epaper-display.local:~/epaper-home-display/data/
```

---

## 文件索引

| 文件 | 說明 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 系統架構、模組分層、asyncio 協程設計、資料流 |
| [docs/configuration.md](docs/configuration.md) | 所有設定項目說明、預設值、config.local.yaml 用法 |
| [docs/development.md](docs/development.md) | 本機開發環境、測試、mock 機制、擴充指南 |
| [docs/deploy-and-test.md](docs/deploy-and-test.md) | Pi 首次部署、日常更新、SSH 金鑰設定、硬體測試 |
| [docs/hardware-wiring.md](docs/hardware-wiring.md) | 完整硬體接線圖與 GPIO 腳位說明 |
| [docs/mqtt-protocol.md](docs/mqtt-protocol.md) | MQTT 主題清單與 JSON 訊息格式規範 |
| [docs/webui.md](docs/webui.md) | WebUI 設定介面完整使用說明與 REST API 參考 |

---

## 架構概覽

```
筆電（開發）                Raspberry Pi Zero 2W
─────────────               ──────────────────────────────────────────────
編輯程式碼                   app/main.py（asyncio 9 協程）
跑單元測試（mock）              ├── _sensor_loop()         → DHT22, 光線（每 30 秒）
git push                        ├── _presence_loop()       → 占用計分, 告警決策（每 60 秒）
                                ├── _display_loop()        → e-Paper 更新（牆鐘 :57）
Agent 1（MQTT）                 ├── _weather_loop()        → OpenWeatherMap（每 600 秒）
─────────────                   ├── _claude_usage_loop()   → Claude 使用量（每 600 秒）
                                ├── _codex_usage_loop()    → Codex 使用量（每 600 秒）
                                ├── _notification_loop()   → Discord 排程通知
                                ├── _wifi_monitor_loop()   → WiFi 模式監測（每 10 秒）
                                └── server.serve()         → FastAPI WebUI（:8000）
home/security/*  →
                                app/ 層架構：
← home/home_state/presence ✓     sensors/ → display/ → logic/ → services/ → storage/
← home/home_state/* (部分計劃中)
                                                ↕
                                           state.py（全局狀態）

                                SQLite（data/*.db）
                                └── 10 張資料表：環境、門、人臉、告警、
                                        圖片、桌面時段、通知等
```

---

## 系統需求

- **Python 3.11+**（開發與 Pi）
- **Pi OS Bookworm / Trixie**（部署目標）；Windows / macOS / Linux（開發端）
- **MQTT Broker**（如 Mosquitto，建議部署在區域網路內）
- **OpenWeatherMap API Key**（免費方案即可，每日 1000 次請求限額）

---

## 相關專案

- **Agent 1**：門鈴攝影機 + 人臉辨識端，透過 MQTT 發布安全事件至本專案
