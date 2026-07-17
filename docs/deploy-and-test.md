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
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install adafruit-circuitpython-dht spidev RPi.GPIO gpiozero'

# 4. 複製設定檔並填入金鑰與 IP
ssh pi@epaper-display.local 'cp ~/epaper-home-display/config.example.yaml ~/epaper-home-display/config.yaml'
# 接著編輯 config.yaml，填入 weather.api_key 等

# 5. 跑單元測試確認邏輯層正常
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m pytest --tb=short'
```

### 一鍵完成 sudoers + systemd 安裝與啟用

以上 5 步只完成到「服務可以手動啟動」；要讓 `epaper-home-display.service`／`epaper-wifi-check.service`／`epaper-auto-update.timer` 開機自動啟動，還需要安裝 sudoers 規則與 systemd 單元檔（需要 sudo，Claude 無法透過 SSH 代執行）。`scripts/setup.sh` 是冪等的一鍵腳本，涵蓋這整段手動流程（sudoers、複製全部 4 個 systemd 單元檔、`daemon-reload`、`enable`、啟動所有服務），建議直接在 Pi 終端機執行：

```bash
bash ~/epaper-home-display/scripts/setup.sh
```

下方第六節「自動更新機制」與第八節手動安裝步驟為此腳本的手動拆解版本，供腳本失敗時逐步除錯用。`scripts/setup-wifi-manager.sh` 只涵蓋 WiFi 相關 sudoers 與 systemd 單元的子集，功能已被 `setup.sh` 完整涵蓋，一般部署不需要單獨執行它。

---

## 四、部署更新到 Pi

### 前置條件

- Pi 已完成首次部署（見第三節）
- Pi 上已有 `~/epaper-home-display` 目錄與 `.venv`

### 日常部署流程（自動更新已啟用）

自動更新 timer 每 5 分鐘檢查一次，有新 commit 就自動 pull 並重啟服務。**只需要 push，Pi 會自行更新**：

```bash
# 1. 本機確認測試全過
pytest

# 2. push 到遠端 → Pi 最多 5 分鐘內自動更新
git push

# 3. 確認自動更新日誌（約 5 分鐘後）
ssh pi@epaper-display.local 'journalctl -t epaper-auto-update -n 20 --no-pager'
```

### 手動部署（緊急或自動更新未設定時）

```bash
ssh pi@epaper-display.local 'cd ~/epaper-home-display && git pull'
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/pip install -r requirements.txt'
ssh pi@epaper-display.local 'sudo systemctl restart epaper-home-display'
ssh pi@epaper-display.local 'systemctl status epaper-home-display --no-pager'
```

### 查看 Log

```bash
# 服務 log（最近 100 行）
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -n 100 --no-pager'

# 服務 log（即時追蹤）
ssh pi@epaper-display.local 'journalctl -u epaper-home-display -f'

# 自動更新 log
ssh pi@epaper-display.local 'journalctl -t epaper-auto-update -n 50 --no-pager'
```

---

## 五、Pi 硬體測試

各硬體模組獨立測試，確認硬體接線與驅動正常：

```bash
# e-Paper 顯示器（Waveshare driver 用 gpiozero，Bookworm/Trixie 需帶 GPIOZERO_PIN_FACTORY=lgpio，見 hardware-wiring.md 1-6 節）
ssh pi@epaper-display.local 'cd ~/epaper-home-display && GPIOZERO_PIN_FACTORY=lgpio .venv/bin/python -m scripts.test_epaper'

# DHT22 溫濕度感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_dht22'

# 光線感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_light'

# 按鈕
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_button'

# 喇叭 / USB 音箱
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_speaker'

# 天氣 API
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_weather'
```

---

## 六、自動更新機制

Pi 上有 systemd timer 每 5 分鐘自動檢查 `origin/main` 是否有新 commit，有則 pull 並重啟服務。

### 首次設定（Pi 首次部署後執行一次）

建議直接執行 `bash ~/epaper-home-display/scripts/setup.sh`（見上方第三節），一次完成 sudoers 規則安裝，以及全部 4 個 systemd 單元檔（`epaper-wifi-check.service`、`epaper-home-display.service`、`epaper-auto-update.service`、`epaper-auto-update.timer`）複製。其中 `epaper-wifi-check.service`、`epaper-home-display.service`、`epaper-auto-update.timer` 會被 `enable`（開機自動啟動）；`epaper-auto-update.service` 是被 timer 觸發的 oneshot 服務，不會、也不需要單獨 enable。以下為手動拆解版本，供腳本失敗時逐步除錯：

```bash
# 1. 腳本加執行權限（epaper-wifi-check.service 直接執行 wifi_manager.sh，epaper-auto-update.service 直接執行 auto_update.sh，兩者在 git 中都不是可執行檔，缺此步驟會 Permission denied）
ssh pi@epaper-display.local 'chmod +x ~/epaper-home-display/scripts/*.sh'

# 2. sudoers：允許 pi 免密重啟服務（在 Pi 上執行，實際權限規則見 scripts/setup.sh）
# sudo tee /etc/sudoers.d/epaper-service > /dev/null << 'EOF'
# pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart epaper-home-display.service
# pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart epaper-wifi-check.service
# EOF
# sudo chmod 440 /etc/sudoers.d/epaper-service

# 3. 安裝並啟用主服務、WiFi 檢查服務與自動更新 timer（在 Pi 上執行）
# sudo cp ~/epaper-home-display/systemd/epaper-wifi-check.service   /etc/systemd/system/
# sudo cp ~/epaper-home-display/systemd/epaper-home-display.service /etc/systemd/system/
# sudo cp ~/epaper-home-display/systemd/epaper-auto-update.service  /etc/systemd/system/
# sudo cp ~/epaper-home-display/systemd/epaper-auto-update.timer    /etc/systemd/system/
# sudo systemctl daemon-reload
# sudo systemctl enable --now epaper-wifi-check.service epaper-home-display.service epaper-auto-update.timer
```

> Step 2–3 需要 sudo，請在 Pi 終端機直接執行（無法透過 Claude SSH 代執行）。`epaper-home-display.service` 依賴 `epaper-wifi-check.service`（`After=`/`Wants=`），兩者需一併安裝。

### 監控

```bash
# 確認 timer 狀態與下次執行時間
ssh pi@epaper-display.local 'systemctl list-timers epaper-auto-update.timer --no-pager'

# 查看更新日誌
ssh pi@epaper-display.local 'journalctl -t epaper-auto-update -n 50 --no-pager'
```

### 暫時停用

```bash
# 停用 timer（Pi 上執行）
# sudo systemctl stop epaper-auto-update.timer

# 重新啟用
# sudo systemctl start epaper-auto-update.timer
```

---

## 七、常見問題排查

| 症狀 | 排查方式 |
|------|---------|
| 服務無法啟動 | `journalctl -u epaper-home-display -n 50` 看錯誤訊息 |
| 硬體測試失敗 | 確認接線，再確認 `.venv/bin/pip install -r requirements.txt` 有跑過 |
| 單元測試匯入 GPIO 錯誤 | 檢查 `tests/conftest.py` 的 mock 是否正確覆蓋硬體模組 |
| `Failed to add edge detection` | Pi OS Trixie/Bookworm 需要 lgpio，執行下方修復步驟 |

### Pi OS Trixie / Bookworm：lgpio 修復

Pi OS Trixie（Debian 13）預設 GPIO 後端改為 lgpio，RPi.GPIO 的 edge detection 會失敗。

```bash
# 1. 安裝系統套件
sudo apt-get install -y swig python3-lgpio

# 2. 將系統 lgpio 路徑加入 venv
SITE=$(cd ~/epaper-home-display && .venv/bin/python -c "import site; print(site.getsitepackages()[0])")
echo "/usr/lib/python3/dist-packages" > "$SITE/system-lgpio.pth"

# 3. 執行硬體腳本時加上環境變數
GPIOZERO_PIN_FACTORY=lgpio .venv/bin/python -m scripts.test_epaper
```
