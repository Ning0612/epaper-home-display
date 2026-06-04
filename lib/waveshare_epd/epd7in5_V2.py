# *****************************************************************************
# * | File        :   epd7in5_V2.py
# * | Author      :   Waveshare team (adapted for epaper-home-display)
# * | Function    :   Electronic paper driver — 7.5" B&W V2 (800×480)
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2024-01-01
# # | Info        :   python demo
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from . import epdconfig

from PIL import Image

# Display resolution
EPD_WIDTH  = 800
EPD_HEIGHT = 480

logger = logging.getLogger(__name__)


class EPD:
    def __init__(self):
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin    = epdconfig.DC_PIN
        self.busy_pin  = epdconfig.BUSY_PIN
        self.cs_pin    = epdconfig.CS_PIN
        self.width     = EPD_WIDTH
        self.height    = EPD_HEIGHT

    # ------------------------------------------------------------------ low-level

    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20)

    def send_command(self, command):
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data2(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte2(data)
        epdconfig.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        logger.debug("e-Paper busy")
        while epdconfig.digital_read(self.busy_pin) == 1:   # 1: busy, 0: idle
            epdconfig.delay_ms(10)
        logger.debug("e-Paper busy release")

    def TurnOnDisplay(self):
        self.send_command(0x22)   # DISPLAY_UPDATE_CONTROL_2
        self.send_data(0xF7)
        self.send_command(0x20)   # MASTER_ACTIVATION
        self.ReadBusy()

    def TurnOnDisplay_Fast(self):
        self.send_command(0x22)   # DISPLAY_UPDATE_CONTROL_2
        self.send_data(0xC7)      # fast mode sequence
        self.send_command(0x20)   # MASTER_ACTIVATION
        self.ReadBusy()

    # ------------------------------------------------------------------ init

    def init(self):
        if epdconfig.module_init() != 0:
            return -1

        self.reset()

        self.ReadBusy()
        self.send_command(0x12)   # SW_RESET
        self.ReadBusy()

        self.send_command(0x01)   # DRIVER_OUTPUT_CONTROL
        self.send_data(0xDF)      # (EPD_HEIGHT - 1) & 0xFF = 479 = 0x1DF
        self.send_data(0x01)      # (EPD_HEIGHT - 1) >> 8
        self.send_data(0x00)      # GD=0 SM=0 TB=0

        self.send_command(0x11)   # DATA_ENTRY_MODE_SETTING
        self.send_data(0x03)      # X increment, Y increment

        self.send_command(0x44)   # SET_RAM_X_ADDRESS_START_END_POSITION
        self.send_data(0x00)      # RAM X start = 0
        self.send_data(0x63)      # RAM X end = 99 (800/8 - 1)

        self.send_command(0x45)   # SET_RAM_Y_ADDRESS_START_END_POSITION
        self.send_data(0x00)
        self.send_data(0x00)      # RAM Y start = 0
        self.send_data(0xDF)
        self.send_data(0x01)      # RAM Y end = 479

        self.send_command(0x3C)   # BORDER_WAVEFORM_CONTROL
        self.send_data(0x05)

        self.send_command(0x21)   # DISPLAY_UPDATE_CONTROL_1
        self.send_data(0x00)
        self.send_data(0x80)

        self.send_command(0x18)   # READ_BUILT_IN_TEMPERATURE_SENSOR
        self.send_data(0x80)

        self.send_command(0x4E)   # SET_RAM_X_ADDRESS_COUNTER
        self.send_data(0x00)
        self.send_command(0x4F)   # SET_RAM_Y_ADDRESS_COUNTER
        self.send_data(0x00)
        self.send_data(0x00)
        self.ReadBusy()
        return 0

    def init_fast(self):
        if epdconfig.module_init() != 0:
            return -1

        self.reset()

        self.send_command(0x12)   # SW_RESET
        self.ReadBusy()

        self.send_command(0x18)   # READ_BUILT_IN_TEMPERATURE_SENSOR
        self.send_data(0x80)

        self.send_command(0x11)   # DATA_ENTRY_MODE_SETTING
        self.send_data(0x03)

        self.send_command(0x44)   # SET_RAM_X_ADDRESS_START_END_POSITION
        self.send_data(0x00)
        self.send_data(0x63)

        self.send_command(0x45)   # SET_RAM_Y_ADDRESS_START_END_POSITION
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0xDF)
        self.send_data(0x01)

        self.send_command(0x4E)   # SET_RAM_X_ADDRESS_COUNTER
        self.send_data(0x00)
        self.send_command(0x4F)   # SET_RAM_Y_ADDRESS_COUNTER
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x22)   # DISPLAY_UPDATE_CONTROL_2 — mode 1 fast
        self.send_data(0xB1)
        self.send_command(0x20)   # MASTER_ACTIVATION
        self.ReadBusy()
        return 0

    # ------------------------------------------------------------------ buffer

    def getbuffer(self, image):
        imwidth, imheight = image.size
        if imwidth == self.width and imheight == self.height:
            image_temp = image
        elif imwidth == self.height and imheight == self.width:
            image_temp = image.rotate(90, expand=True)
        else:
            logger.warning(
                "Invalid image dimensions: %d x %d, expected %d x %d",
                imwidth, imheight, self.width, self.height,
            )
            image_temp = image

        # Convert to 1-bit: white=255→1 bit, black=0→0 bit.
        # PIL mode "1" packs 8 pixels per byte, MSB first.
        bw = image_temp.convert("RGB").convert("1")
        return bytearray(bw.tobytes("raw", "1"))

    # ------------------------------------------------------------------ display

    def display(self, image):
        self.send_command(0x24)   # WRITE_RAM_BW
        self.send_data2(image)
        self.TurnOnDisplay()

    def display_fast(self, image):
        self.send_command(0x24)   # WRITE_RAM_BW
        self.send_data2(image)
        self.TurnOnDisplay_Fast()

    def Clear(self, color=0xFF):
        buf = [color] * (self.width * self.height // 8)
        self.send_command(0x24)
        self.send_data2(buf)
        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x10)   # DEEP_SLEEP_MODE
        self.send_data(0x01)      # enter deep sleep

        epdconfig.delay_ms(2000)
        epdconfig.module_exit()

### END OF FILE ###
