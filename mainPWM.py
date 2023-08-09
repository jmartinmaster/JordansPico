###Generates PWM to fade Pin 25 (Built in LED)

from time import sleep
from machine import Pin
fr = 0
led = machine.PWM(Pin(25))
led.freq(10000)
sT=0.001
max_count = 65530
while True:
    while fr < max_count:
        fr = fr + 100
        led.duty_u16(fr)
        sleep(0.003)
    while fr > 0:
        fr = fr - 100
        led.duty_u16(fr)
        sleep(0.003)
