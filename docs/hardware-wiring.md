# 硬體接線指南

目標板：Raspberry Pi Zero 2W  
顯示器：Waveshare 7.5" e-Paper (V2)

---

## Pi Zero 2W 腳位總覽

```
         3V3  1 ● ○  2  5V
   (DHT22) 4  3 ● ○  4  5V
           -  5 ○ ○  6  GND ← 多元件共地
       DHT22  7 ● ○  8
         GND  9 ● ●  10
  (Button) 27 11 ○ ●  11  ← 電子紙 RST（勿用）
              13 ● ○  12
  (Button) 27 13 ●  ← 按鈕
              14 GND
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

## 1. Waveshare 7.5" e-Paper (V2)

直接插上 Pi 的 40-pin 排針即可（HAT 形式）。

若使用排線連接，對應腳位如下：

| e-Paper 標籤 | Pi 腳位 | GPIO (BCM) |
|-------------|---------|-----------|
| VCC | Pin 1 | 3.3V |
| GND | Pin 6 | GND |
| DIN | Pin 19 | GPIO 10 (SPI MOSI) |
| CLK | Pin 23 | GPIO 11 (SPI SCLK) |
| CS | Pin 24 | GPIO 8 (CE0) |
| DC | Pin 22 | GPIO 25 |
| RST | Pin 11 | GPIO 17 |
| BUSY | Pin 18 | GPIO 24 |

> **⚠️ 注意**：GPIO 17 (Pin 11) 已被 e-Paper RST 佔用，**按鈕不可使用此腳位**。

### 安裝 Waveshare 驅動

驅動未包含在 repo，需手動下載：

```bash
ssh pi@epaper-display.local
cd ~/epaper-home-display/lib/waveshare_epd

# 下載兩個必要檔案
wget https://raw.githubusercontent.com/waveshare/e-Paper/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd7in5_V2.py
wget https://raw.githubusercontent.com/waveshare/e-Paper/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epdconfig.py
```

啟用 SPI（若尚未啟用）：

```bash
sudo raspi-config
# Interface Options → SPI → Enable
sudo reboot
```

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
# 1. 電子紙
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_epaper'

# 2. DHT22
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_dht22'

# 3. 光線感測器
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_light'

# 4. 按鈕
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_button'

# 5. 喇叭
ssh pi@epaper-display.local 'cd ~/epaper-home-display && .venv/bin/python -m scripts.test_speaker'
```
