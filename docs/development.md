# 開發指南

## 開發環境準備（首次）

### 系統需求

- Python 3.11+
- Windows / macOS / Linux（筆電開發端）
- Git

### 建立虛擬環境

```bash
cd epaper-home-display
python -m venv .venv
```

### 安裝依賴

**Windows：**
```bash
.venv\Scripts\pip install -r requirements.txt
```

**macOS / Linux：**
```bash
.venv/bin/pip install -r requirements.txt
```

> Pi 專屬套件（`adafruit-circuitpython-dht`, `spidev`, `RPi.GPIO`, `gpiozero`）在筆電上**不安裝**，由 mock 機制替代。

---

## 執行測試

### 全部測試

```bash
pytest
```

### 指定測試檔案

```bash
pytest tests/test_presence.py
```

### 指定測試函式

```bash
pytest tests/test_presence.py::test_light_dark_is_occupied
```

### 語法檢查

```bash
# 單一檔案
.venv/Scripts/python.exe -m py_compile app/logic/presence.py

# 整個目錄
.venv/Scripts/python.exe -m compileall app/
```

---

## Mock 機制

測試和本機開發不需要任何硬體。所有硬體模組有對應的 mock 實作。

### 測試中的 Mock

`tests/conftest.py` 在任何 `app` 模組被引入之前，設定環境變數強制 mock 模式：

```python
import os
os.environ["RPI_MOCK"] = "1"
```

### 本機開發中的 Mock

`config.yaml` 或 `config.local.yaml` 設定 `use_mock: true`：

```yaml
sensors:
  dht22:
    use_mock: true
  light:
    use_mock: true
  button:
    use_mock: true
display:
  use_mock: true
```

### Mock 回傳值

| 模組 | Mock 回傳 |
|------|---------|
| `MockDHT22.read()` | `(26.0, 60.0)` — 溫度 26°C，濕度 60% |
| `MockLightSensor.read_raw()` | `500` — 中等亮度 |
| `MockLightSensor.is_bright()` | `True` |
| `MockButton` | 不觸發任何 GPIO 事件 |
| `MockEpaper.display()` | 儲存 Pillow Image 到 `debug_frame.png`（可視覺檢查）|

---

## 測試覆蓋範圍

| 測試檔案 | 涵蓋模組 | 測試數量 |
|---------|---------|---------|
| `test_presence.py` | `app/logic/presence.py` | 6+ 個測試案例 |
| `test_alarm_decision.py` | `app/logic/alarm_decision.py` | 決策樹所有路徑 |
| `test_reminder.py` | `app/logic/reminder.py` | 各提醒觸發條件 |
| `test_door_reminder.py` | `app/logic/door_reminder.py` | 開門提醒文字生成（天氣情境、無資料備援）|
| `test_face_handler.py` | `app/services/mqtt_client.py`（face dispatch）| vote_result 正規化、sentinel 處理、known 推導 |
| `test_voice_config.py` | `app/services/voice.py`（設定解析）| 語音設定驗證 |
| `test_renderer.py` | `app/display/renderer.py` | 圖像渲染（Pillow mock）|
| `test_state.py` | `app/state.py` | 狀態初始化與更新 |
| `test_desk_session.py` | `app/logic/desk_session.py` | 桌面工作時段狀態機 |
| `test_image_processor.py` | `app/display/image_processor.py` | 圖片裁切與 dithering（六色量化）|
| `test_carousel.py` | `app/loops/display.py`（輪播邏輯）| 圖片輪播換圖行為 |
| `test_weather_service.py` | `app/services/weather.py` | API 回應解析（aiohttp mock）|

> **注意**：`tests/conftest.py` 為全域測試前置設定，強制設定 `RPI_MOCK=1` 環境變數，確保所有測試均使用 mock 硬體，不需也不應在 Pi 以外的環境安裝 GPIO 套件。

> **測試覆蓋缺口**：以下新增模組目前尚無直接測試，邊界條件未受回歸保護：`app/services/wifi_monitor.py`（AP 狀態檔損壞、nmcli 失敗）、`app/services/snapshot_client.py`（逾時、大檔案拒絕）、`app/display/renderer_alert.py`、`app/display/renderer_apmode.py`、`app/webui/routes/wifi.py`（未認證 WiFi API 行為）。有意新增測試覆蓋時可優先補上這些模組。

---

## 本機執行主服務（無硬體）

使用 mock 配置可在筆電上執行完整服務（但不連 MQTT 和真實硬體）：

1. 建立 `config.local.yaml`：

```yaml
sensors:
  dht22:
    use_mock: true
  light:
    use_mock: true
  button:
    use_mock: true
display:
  use_mock: true
mqtt:
  broker_host: "localhost"
weather:
  api_key: "your_api_key_here"
```

2. 執行：

```bash
.venv/Scripts/python.exe -m app.main
```

WebUI 將在 `http://localhost:8000` 提供服務。

---

## 程式碼結構指南

### 新增感測器

1. 在 `app/sensors/` 建立新模組
2. 定義 `Protocol` 介面、`Real` 實作和 `Mock` 實作
3. 提供 `create_xxx(config)` factory 函數
4. 在 `app/config.py` 新增對應的配置 dataclass
5. 在 `config.example.yaml` 新增設定範例
6. 在 `tests/` 加入 mock 測試

### 新增業務邏輯

業務邏輯必須是**純函數**（`app/logic/`）：

```python
# 正確：接收資料，回傳結果，無副作用
def compute_something(data: SomeInput, config: SomeConfig) -> SomeOutput:
    ...

# 錯誤：直接讀取 state 或呼叫 GPIO
def compute_something():
    temp = state.temperature  # 不應這樣做
    ...
```

純函數可獨立進行單元測試，不需要 mock 任何外部依賴。

### 新增 MQTT 主題

1. 在 `app/services/mqtt_client.py` 的 `_dispatch()` 方法中新增 topic 處理
2. 在 `app/storage/logs.py` 新增對應的日誌函數
3. 更新 `docs/mqtt-protocol.md`

### 修改顯示佈局

渲染邏輯拆分於 `app/display/` 下的多個模組，顯示器解析度為 800×480 像素（`"RGB"` 模式，對應 7.3" 六色面板）。

```python
# app/display/renderer.py - 主入口
def render_dashboard(state: AgentState, settings: Settings, now: datetime | None = None) -> Image.Image:
    img = Image.new("RGB", (800, 480), (255, 255, 255))  # 白色背景，RGB 模式（6 色面板）
    draw = ImageDraw.Draw(img)
    # 各卡片繪製函數在 renderer_cards.py
    return img
```

各卡片繪製函數在 `app/display/renderer_cards.py`，版面常數在 `renderer_constants.py`，工具函數（天氣圖示、進度條等）在 `renderer_utils.py`。

使用 `MockEpaper` 可將渲染結果儲存為 `debug_frame.png` 進行視覺驗證。

---

## 設定管理

### 配置優先度

```
config.local.yaml > config.yaml > 程式碼預設值
```

### config.local.yaml 的用途

`config.local.yaml` 用於本機開發覆蓋，只需寫需要覆蓋的部分：

```yaml
# config.local.yaml（本機 API key，git ignored）
weather:
  api_key: "my_local_api_key"
```

### 環境變數覆蓋

目前唯一支援的環境變數覆蓋：

```bash
RPI_MOCK=1  # 強制所有硬體使用 mock
```

> **注意**：`RPI_MOCK=1` 以外的設定（MQTT broker、Weather API key 等）**不支援**透過環境變數覆蓋，請使用 `config.local.yaml`。

---

## Git 工作流程

```bash
# 開始新功能
git checkout -b feature/your-feature-name

# 測試通過後 commit
pytest
git add app/ tests/
git commit -m "feat: your feature description"

# Push 並部署
git push
ssh pi@epaper-display.local 'cd ~/epaper-home-display && git pull && sudo systemctl restart epaper-home-display'
```

---

## 常見問題

### 測試時出現 `ImportError: No module named 'RPi'`

確認 `tests/conftest.py` 正確設定 `RPI_MOCK=1`，且 mock 模組有覆蓋所有硬體引入。

### 本機執行時出現 `MQTT connection refused`

MQTT Broker 在本機未執行是正常的。設定 `config.local.yaml` 指向實際的 Broker，或接受連線失敗後服務仍繼續運行的行為。

### `config.yaml` 不存在

複製範本：
```bash
cp config.example.yaml config.yaml
```

### Pillow 字體找不到

確認 `assets/fonts/DejaVuSans.ttf` 和 `DejaVuSans-Bold.ttf` 存在。這些字體應已包含在 repo 中。
