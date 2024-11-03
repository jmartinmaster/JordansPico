from machine import Pin, SPI
import st7789  # Ensure you have the correct display driver library

def setup_display():
    spi = SPI(1, baudrate=40000000, polarity=1, phase=1, sck=Pin(10), mosi=Pin(11))
    tft = st7789.ST7789(spi, 240, 240, reset=Pin(12, Pin.OUT), cs=Pin(9, Pin.OUT), dc=Pin(8, Pin.OUT), backlight=Pin(13, Pin.OUT))
    tft.init()

    return tft

def draw_text(tft, text, x, y):
    tft.fill(st7789.BLACK)
    tft.text(tft.FONT_DEFAULT, text, x, y, st7789.WHITE)
