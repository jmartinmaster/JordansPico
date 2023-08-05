from time import sleep
from machine import Pin
fr = 0
led = machine.PWM(Pin(25))
led.freq(10000)
sT=0.03
max_count = 65530
while True:
    while fr < max_count:
        fr = fr + 10
        led.duty_u16(fr)
        utime.sleep_ns(0.03)
    while fr > 0:
        fr = fr - 10
        led.duty_u16(fr)
        utime.sleep_ns(0.03)