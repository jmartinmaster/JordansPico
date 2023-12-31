from machine import Pin,PWM
from time import sleep
import _thread
#This runs PIO from Core1 outputting PWM to Pin(25)
#leaving core0 to do other stuffs. Thread for core1 can 
#be loaded to run several things as State machine runs at 0.1MHz
#and Pico core is at 125MHz
#This allows for PWM output on unused core without interrupting main, Core0
newLock = _thread.allocate_lock()

pins = [25, 28, 16, 17, 18, 19, 13,24 ]
pinInt = [0,1,2,3,4,5,6,7]
ground = 12
pinV = [0, 0, 0, 65500, 65500, 65500, 65500, 65500]
#random.randint()/1000 may generate and invalid decimal that will lock the core it running on
pinFV= [100,120,110,130,111,120,110]
pinDelay= [0.001,0.002,0.001,0.002,0.001,0.003,0.001]
sT = 0.001
fr = 0
fV = 100
max_count = 65530
min_count = 3000
pin = 0
value = 0
PWMLock = newLock
Thread_Break = newLock
pins[0] = PWM(Pin(25)) #G10
pins[1] = PWM(Pin(28)) #G9
pins[2] = PWM(Pin(16)) #G0
pins[3] = PWM(Pin(17)) #G1
pins[4] = PWM(Pin(18)) #G2
pins[5] = PWM(Pin(19)) #G3
pins[6] = PWM(Pin(13)) #PWM0
pins[7] = PWM(Pin(24)) #PWM1
#led = PWM(Pin(25))
def setup1():
    pins[0].freq(10000)
    pins[1].freq(10000)
    pins[2].freq(10000)
    pins[3].freq(10000)
    pins[4].freq(10000)
    pins[5].freq(10000)
    pins[6].freq(10000)
    pins[7].freq(10000)

    #led.freq(1000)
    pins[0].duty_u16(65500)
    pins[1].duty_u16(65500)
    pins[2].duty_u16(65500)
    pins[3].duty_u16(65500)
    pins[4].duty_u16(65500)
    pins[5].duty_u16(65500)
    pins[6].duty_u16(65500)
    pins[7].duty_u16(65500)
    #led.duty_u16(65530)

def pinFaderUp():
    global pins
    global pinV
    global pinFV
    global pin
    global value
    PWMLock.acquire()
    if (pinV[pin] < value):
        while (pinV[pin] < value):
            pinV[pin] = pinV[pin] + pinFV[pin]
            if (pinV[pin] > 65500):
                pinV[pin] = 65500
        pins[pin].duty_u16(pinV[pin])
        sleep(0.001)
    PWMLock.release()

def pinFaderDown():
    global pins
    global pinV
    global pinFV
    global pin
    global value    
    PWMLock.acquire()
    if (pinV[pin] > value):
        while (pinV[pin] > value):
            pinV[pin] = pinV[pin] - pinFV[pin]
        if (pinV[pin] < 0 ):
            pinV[pin] = 0
        pins[pin].duty_u16(pinV[pin])
        sleep(0.001)
    PWMLock.release()


def core1_village_houses():
    print("hello")
second_thread = _thread.start_new_thread(core1_village_houses, ())
def primary():
    global fr
    global fV
    global sT
    global max_count
    global min_count
    global pinInt
    while fr < max_count:
        fr = fr + fV
        pins[pin].duty_u16(fr)
        sleep(sT)
    while fr > min_count:
        fr = fr - fV
        pins[pin].duty_u16(fr)
        sleep(sT)
def loop():
    global pin
    while True:
        pin = 0
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 1
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 2
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 3
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 4
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 5
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 6
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
        pin = 7
        second_thread = _thread.start_new_thread(primary, ())
        sleep(2)
setup1()
loop()
#second_thread = _thread.start_new_thread(loop, ())