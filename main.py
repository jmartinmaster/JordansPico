from machine import Pin, PWM
from time import sleep
import _thread

newLock = _thread.allocate_lock()

pins = [PWM(Pin(25)), PWM(Pin(28)), PWM(Pin(16)), PWM(Pin(17)), PWM(Pin(18)), PWM(Pin(19)), PWM(Pin(13)), PWM(Pin(24))]
outPutEnable = Pin(20, Pin.OUT)

pinV = [0, 0, 0, 65500, 65500, 65500, 65500, 65500]
pinFV = [100, 120, 110, 130, 111, 120, 110, 130]
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.001, 0.003, 0.001, 0.002]
sT = 0.001
fr = 0
fV = 100
max_count = 65530
min_count = 0
pin = 0
value = 0
PWMLock = newLock

def setup1():
    for p in pins:
        p.freq(10000)
        p.duty_u16(65500)

def pinFaderUp():
    global pinV, pinFV, pin, value, PWMLock
    PWMLock.acquire()
    try:
        if pinV[pin] < value:
            while pinV[pin] < value:
                pinV[pin] += pinFV[pin]
                if pinV[pin] > 65500:
                    pinV[pin] = 65500
                pins[pin].duty_u16(pinV[pin])
                sleep(0.001)
    finally:
        PWMLock.release()

def pinFaderDown():
    global pinV, pinFV, pin, value, PWMLock
    PWMLock.acquire()
    try:
        if pinV[pin] > value:
            while pinV[pin] > value:
                pinV[pin] -= pinFV[pin]
                if pinV[pin] < 0:
                    pinV[pin] = 0
                pins[pin].duty_u16(pinV[pin])
                sleep(0.001)
    finally:
        PWMLock.release()

def core1_village_houses():
    print("hello")
    
second_thread = _thread.start_new_thread(core1_village_houses, ())

def toggleEO():
    outPutEnable.value(0)
    sleep(0.002)
    outPutEnable.value(1)

def primary():
    global fr, fV, sT, max_count, min_count
    while fr < max_count:
        fr += fV
        pins[pin].duty_u16(fr)
        sleep(sT)
    while fr > min_count:
        fr -= fV
        pins[pin].duty_u16(fr)
        sleep(sT)

def loop():
    global pin
    while True:
        for i in range(8):
            pin = i
            toggleEO()
            _thread.start_new_thread(primary, ())
            toggleEO()
            sleep(2)

setup1()
loop()
