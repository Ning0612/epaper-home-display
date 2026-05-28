# 部署與測試指南

## 概述

開發在筆電上進行，Pi 只負責跑 service 與硬體測試。

```
筆電  →  編輯程式碼 / 跑單元測試 / commit / push
Pi    →  git pull / 跑硬體測試 / 跑 service
```

---

## 一、本機開發（筆電）

### 環境準備（首次）

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

### 單元測試

```bash
# 全部測試
pytest

# 單一檔案
pytest tests/test_presence.py

# 單一函式
pytest tests/test_presence.py::test_occupied_when_light_bright
```

### 語法檢查

```bash
# 單一檔案
.venv/Scripts/python.exe -m py_compile app/logic/presence.py

# 整個目錄
.venv/Scripts/python.exe -m compileall app/
```

---

## 二、SSH 金鑰設定（首次）

第一次連線 Pi 需設定金鑰，完成後所有 SSH / SCP 操作都不需輸入密碼。

### 筆電端：產生金鑰

```bash
ssh-keygen -t ed25519 -C "epaper-display"
# 三個提示全部按 Enter（使用預設路徑、空 passphrase）
```

金鑰會產生在 `~/.ssh/id_ed25519`（私鑰）與 `~/.ssh/id_ed25519.pub`（公鑰）。

### 複製公鑰到 Pi（只需做一次，需輸入密碼）

```bash
# Linux / macOS
ssh-copy-id pi@epaper-display.local

# Windows（ssh-copy-id 不存在時改用此指令）
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh pi@epaper-display.local "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### 驗證

```bash
ssh pi@epaper-display.local 'echo "連線成功"'
# 不需要輸入密碼即可看到輸出
```

---

## 三、Pi 首次部署

### 前置條件

- Pi 已開機、SSH 金鑰已設定（見第二節）
- GitHub repo：`https://github.com/Ning0612/epaper-home-display.git`

### 首次部署流程

```bash
# 1. Clone 專案
ssh pi@epaper-display.local 'git clone https://github.com/Ning0612/epaper-home-display.git ~/epaper-home-display'

# 2. 建立虛擬環境
ssh pi@epaper-display.local 'cd ~/epaper-home-display && python3 -m venv .venv'

# 3. 安裝依賴（含 Pi 硬體套件）
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install -r requirements.txt'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install adafruit-circuitpython-dht spidev RPi.GPIO'

# 4. 複製設定檔並填入金鑰與 IP
ssh pi@epaper-display.local 'cp ~/epaper-home-display/config.example.yaml ~/epaper-home-display/config.yaml'
# 接著編輯 config.yaml，填入 mqtt_broker_host、weather.api_key 等

# 5. 跑單元測試確認邏輯層正常
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m pytest --tb=short'
```

---

## 四、部署更新到 Pi

### 前置條件

- Pi 已完成首次部署（見第三節）
- Pi 上已有 `~/epaper-home-display` 目錄與 `.venv`

### 日常部署流程

```bash
# 1. 本機確認測試全過
pytest

# 2. push 到遠端
git push

# 3. Pi 拉取最新程式碼
ssh pi@epaper-display.local 'cd ~/epaper-home-display && git pull'

# 4. 更新套件（依賴有變動時才需要）
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install -r requirements.txt'

# 5. 重啟服務
ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'

# 6. 確認服務狀態
ssh pi@epaper-display.local 'systemctl status epaper-home-display --no-pager'
```

### 查看 Log

```bash
# 最近 100 行
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -n 100 --no-pager'

# 即時追蹤
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -f'
```

---

## 五、Pi 硬體測試

各硬體模組獨立測試，確認硬體接線與驅動正常：

```bash
# e-Paper 顯示器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_epaper'

# DHT22 溫濕度感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_dht22'

# 光線感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_light'

# 按鈕
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_button'

# 喇叭 / USB 音箱
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_speaker'

# MQTT 連線
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_mqtt'

# 天氣 API
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_weather'
```

---

## 六、常見問題排查

| 症狀 | 排查方式 |
|------|---------|
| 服務無法啟動 | `journalctl -u epaper-home-display -n 50` 看錯誤訊息 |
| 硬體測試失敗 | 確認接線，再確認 `.venv/bin/pip install -r requirements.txt` 有跑過 |
| 單元測試匯入 GPIO 錯誤 | 檢查 `tests/conftest.py` 的 mock 是否正確覆蓋硬體模組 |
| MQTT 無法連線 | 確認 `config.yaml` 的 `mqtt_broker_host` 設定正確 |
