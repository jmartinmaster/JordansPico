from machine import Pin, PWM
from time import sleep
import random

# Set up PWM pins
pins = [PWM(Pin(3)), PWM(Pin(5)), PWM(Pin(6)), PWM(Pin(4)), PWM(Pin(9)), PWM(Pin(10)), PWM(Pin(11))]
pinV = [0, 0, 0, 255, 255, 255, 255]
pinFV = [random.randint(2, 15), random.randint(2, 15), random.randint(2, 15), random.randint(2, 15), random.randint(2, 15), random.randint(2, 15), random.randint(2, 15)]
pinDelay = [random.randint(10, 60) / 1000, random.randint(10, 60) / 1000, random.randint(10, 60) / 1000, random.randint(10, 60) / 1000, random.randint(20, 70) / 1000, random.randint(20, 70) / 1000, random.randint(20, 70) / 1000]

mode = 4  # Set initial mode
ssdelay = 0.05  # Initial delay

def setup_pins():
    for p in pins:
        p.freq(1000)  # Set frequency for all pins

def speed_strip():
    global ssdelay
    if mode in [4, 5, 6]:
        val = random.randint(0, 300)
        if val > 268 or val < 0:
            ssdelay = 0.005
        if 0 < val < 20:
            ssdelay = 0.02
        elif 20 < val < 30:
            ssdelay = 0.07
        elif 30 < val < 40:
            ssdelay = 0.08
        elif 40 < val < 60:
            ssdelay = 0.1
        elif 60 < val < 80:
            ssdelay = 0.13
        elif 80 < val < 100:
            ssdelay = 0.16
        elif 100 < val < 120:
            ssdelay = 0.2
        elif 120 < val < 140:
            ssdelay = 0.25
        elif 140 < val < 160:
            ssdelay = 0.3
        elif 160 < val < 190:
            ssdelay = 0.35
        elif 190 < val < 220:
            ssdelay = 0.4
        elif 220 < val < 240:
            ssdelay = 0.6
        elif 240 < val < 268:
            ssdelay = 0.8
        elif 268 < val < 280:
            ssdelay = 0.85
        elif 280 < val < 290:
            ssdelay = 0.875
        elif 290 < val < 300:
            ssdelay = 0.9
        if mode in [4, 5]:
            ssdelay /= 30

    elif mode in [0, 1, 2, 3]:
        val = random.randint(0, 300)
        if val < 125:
            ssdelay = 0.001
        else:
            ssdelay = 0.002

def pin_fader_m5(pin, value):
    global pins, pinV, pinFV, pinDelay, ssdelay
    if pin in [1, 2, 3]:
        if pinV[pin] < value:
            while pinV[pin] < value:
                pinV[pin] += pinFV[pin]
                if pinV[pin] > 65535:
                    pinV[pin] = 65535
                pins[pin].duty_u16(pinV[pin])
                speed_strip()
                sleep(ssdelay)
        elif pinV[pin] > value:
            while pinV[pin] > value:
                pinV[pin] -= pinFV[pin]
                if pinV[pin] < 0:
                    pinV[pin] = 0
                pins[pin].duty_u16(pinV[pin])
                speed_strip()
                sleep(ssdelay)
        if pin == 4:
            pin = 1
    if pin == 5:
        pin = 2
    if pin == 6:
        pin = 3

    while pinV[pin] < value:
        pinV[pin] += pinFV[pin]
        if pinV[pin] > 65535:
            pinV[pin] = 65535
        pins[pin].duty_u16(pinV[pin])
        speed_strip()
        sleep(ssdelay)
    if pinV[pin] > value:
        while pinV[pin] > value:
            pinV[pin] -= pinFV[pin]
            if pinV[pin] < 0:
                pinV[pin] = 0
            pins[pin].duty_u16(pinV[pin])
            speed_strip()
            sleep(ssdelay)

def loop():
    while True:
        pin_fader_m5(1, 65535)  # no green
        pin_fader_m5(4, 0)
        pin_fader_m5(4, 65535)
        pin_fader_m5(2, 65535)  # no red
        pin_fader_m5(5, 0)
        pin_fader_m5(5, 65535)
        pin_fader_m5(1, 0)  # green on
        pin_fader_m5(6, 0)
        pin_fader_m5(6, 65535)
        pin_fader_m5(0, 65535)  # no blue
        pin_fader_m5(4, 0)
        pin_fader_m5(4, 65535)
        pin_fader_m5(2, 0)   # red on
        pin_fader_m5(5, 0)
        pin_fader_m5(5, 65535)
        pin_fader_m5(1, 65535)  # no green
        pin_fader_m5(6, 0)
        pin_fader_m5(6, 65535)
        pin_fader_m5(0, 0)   # blue on
        pin_fader_m5(1, 0)   # green on

setup_pins()
loop()
