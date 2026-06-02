# 硬體接線指南

目標板：Raspberry Pi Zero 2W  
顯示器：Waveshare 7.3" e-Paper (E)（六色：黑、白、紅、黃、藍、綠）

---

## Pi Zero 2W 腳位總覽

```
         3V3  1 ● ○  2  5V
   (DHT22) 4  3 ● ○  4  5V
           -  5 ○ ○  6  GND ← 多元件共地
       DHT22  7 ● ○  8
         GND  9 ○ ○  10
              11 ○ ○  12  ← Pin 11 = GPIO 17（電子紙 RST，勿用）
              13 ● ○  14 GND  ← Pin 13 = GPIO 27（按鈕）
              ...
              18     ← 電子紙 BUSY (GPIO 24)
              19     ← SPI MOSI  (GPIO 10)
              20 GND
              21     ← SPI MISO  (GPIO  9)
              22     ← 電子紙 DC  (GPIO 25)
              23     ← SPI SCLK  (GPIO 11)
              24     ← SPI CE0   (GPIO  8) ← 電子紙 CS
              25 GND
              26     ← SPI CE1   (GPIO  7) ← MCP3008 CS
```

---

## 1. Waveshare 7.3" e-Paper (E)

### 1-1. 實體組裝

連接鏈為：**電子紙面板 → 排線 → e-Paper Adapter → e-Paper Driver HAT (Rev2.3) → Pi 40-pin 排針**

1. 將排線一端插入電子紙面板的 FPC 座（金屬觸點朝下）
2. 排線另一端插入 e-Paper Adapter
3. e-Paper Adapter 接到 Driver HAT 的排線插座
4. Driver HAT 直接插上 Pi Zero 2W 的 40-pin 排針

### 1-2. GPIO 腳位對應

Driver HAT 透過排針佔用以下 GPIO，**這些腳位不可給其他元件使用**：

| e-Paper 信號 | Pi 腳位 | GPIO (BCM) |
|-------------|---------|-----------|
| VCC | Pin 1 | 3.3V |
| GND | Pin 6 | GND |
| DIN (MOSI) | Pin 19 | GPIO 10 |
| CLK (SCLK) | Pin 23 | GPIO 11 |
| CS | Pin 24 | GPIO 8 (CE0) |
| DC | Pin 22 | GPIO 25 |
| **RST** | **Pin 11** | **GPIO 17 ← 按鈕不可用此腳** |
| BUSY | Pin 18 | GPIO 24 |

### 1-3. 啟用 SPI

```bash
ssh pi@epaper-display.local 'ls /dev/spi*'
# 看到 /dev/spidev0.0 和 /dev/spidev0.1 表示已啟用
```

若未出現，執行：

```bash
ssh pi@epaper-display.local 'sudo raspi-config'
# Interface Options → SPI → Enable → 重開機
```

### 1-4. 驅動說明

驅動已內建於 repo 的 `lib/waveshare_epd/` 目錄中（`epd7in3e.py` 與 `epdconfig.py`），**無需手動下載**。`epaper.py` 以 `importlib` 動態載入對應驅動（依 `config.yaml` 中的 `display.model`）。

### 1-5. Pi OS Trixie / Bookworm：lgpio 設定

Pi OS Trixie（Debian 13）與 Bookworm 的 GPIO 後端改為 lgpio，需額外設定：

```bash
# 安裝系統套件
ssh pi@epaper-display.local 'sudo apt-get install -y swig python3-lgpio'

# 將系統 lgpio 加入 venv 可見範圍（只需做一次）
ssh pi@epaper-display.local '
SITE=$(cd ~/epaper-home-display && .venv/bin/python -c "import site; print(site.getsitepackages()[0])")
echo "/usr/lib/python3/dist-packages" > "$SITE/system-lgpio.pth"
echo "lgpio 路徑設定完成"
'
```

### 1-6. 測試電子紙

```bash
ssh pi@epaper-display.local '
cd ~/epaper-home-display &&
GPIOZERO_PIN_FACTORY=lgpio .venv/bin/python -m scripts.test_epaper
'
```

預期輸出：
```
Initialising e-Paper 7.3" (E) ...
  init OK
Clearing display ...
  clear OK
Drawing test image ...
  display OK
  sleep OK
PASS
```

畫面顯示：六色測試圖案（黑/白/紅/黃/藍/綠色塊）+ 中央文字 `ePaper Home Display Test OK`。

---

## 2. DHT22 溫濕度感測器

| DHT22 腳位 | 接到 Pi | 備註 |
|-----------|---------|------|
| VCC (1) | Pin 1 (3.3V) | 也可接 5V |
| DATA (2) | Pin 7 (GPIO 4) | 需接 10kΩ 上拉電阻到 VCC |
| NC (3) | 不接 | |
| GND (4) | Pin 9 (GND) | |

**10kΩ 上拉電阻**：連接在 DATA 與 VCC 之間，DHT22 必須加，否則讀值不穩定。

```
3.3V ──┬── 10kΩ ──┬── GPIO 4
       │           │
      VCC        DATA
       DHT22
       GND ────── GND
```

---

## 3. 光線感測器（光敏電阻 + MCP3008 ADC）

MCP3008 是 10-bit SPI ADC，將類比光敏電阻訊號轉為數位值。

### MCP3008 接線（使用 CE1，不和電子紙衝突）

| MCP3008 腳位 | 接到 Pi | GPIO |
|-------------|---------|------|
| VDD (16) | Pin 1 (3.3V) | |
| VREF (15) | Pin 1 (3.3V) | |
| AGND (14) | Pin 6 (GND) | |
| CLK (13) | Pin 23 | GPIO 11 (SPI SCLK) |
| DOUT (12) | Pin 21 | GPIO 9 (SPI MISO) |
| DIN (11) | Pin 19 | GPIO 10 (SPI MOSI) |
| CS (10) | **Pin 26** | **GPIO 7 (CE1)** |
| DGND (9) | Pin 6 (GND) | |

### 光敏電阻接線（接到 MCP3008 CH0）

```
3.3V ──── 10kΩ ──┬──── MCP3008 CH0 (pin 1)
                  │
               光敏電阻
                  │
                 GND
```

> config.yaml 中 `spi_device: 1`（CE1）已正確設定。

---

## 4. 按鈕

| 按鈕端 | 接到 Pi | 備註 |
|-------|---------|------|
| 一端 | Pin 13 (GPIO 27) | |
| 另一端 | Pin 9 (GND) | 程式碼已啟用內部上拉，按下時讀 LOW |

不需要外部電阻，GPIO 已設定 `pull_up_down=GPIO.PUD_UP`。

> config.yaml 中 `gpio_pin: 27` 已正確設定。

---

## 5. 喇叭 / USB 音箱

直接插入 Pi Zero 2W 的 micro USB OTG 口（使用 OTG 轉接頭）。

確認系統能識別：

```bash
ssh pi@epaper-display.local 'aplay -l'
```

---

## 接線完成後的測試順序

```bash
# 1. 電子紙（需 lgpio，見 1-6 節）
ssh pi@epaper-display.local 'cd ~/epaper-home-display && GPIOZERO_PIN_FACTORY=lgpio .venv/bin/python -m scripts.test_epaper'

# 2. DHT22
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_dht22'

# 3. 光線感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_light'

# 4. 按鈕
ssh pi@epaper-display.local 'cd ~/epaper-home-display && GPIOZERO_PIN_FACTORY=lgpio .venv/bin/python -m scripts.test_button'

# 5. 喇叭
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_speaker'
```
