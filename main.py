from machine import Pin,PWM
from time import sleep
import _thread, random
#This runs PIO from Core1 outputting PWM to Pin(25)
#leaving core0 to do other stuffs. Thread for core1 can 
#be loaded to run several things as State machine runs at 0.1MHz
#and Pico core is at 125MHz
#This allows for PWM output on unused core without interupting main, Core0
newLock = _thread.allocate_lock()

pins = [25, 28, 16, 17, 18, 19, 13,24 ]
pinInt = [0,1,2,3,4,5,6,7]
ground = 12
pinV = [0, 0, 0, 65530, 65530, 65530, 65530, 65530]
#random.randint()/1000 may generate and invalid decimal that will lock the core it running on
pinFV= [100,120,110,130,111,120,110]
pinDelay= [0.001,0.002,0.001,0.002,0.001,0.003,0.001]
sT = 0.001
fr = 0
max_count = 65530
pin = 0
value = 0
PWMLock = newLock
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
    pins[0].duty_u16(65530)
    pins[1].duty_u16(65530)
    pins[2].duty_u16(65530)
    pins[3].duty_u16(65530)
    pins[4].duty_u16(65530)
    pins[5].duty_u16(65530)
    pins[6].duty_u16(65530)
    pins[7].duty_u16(65530)
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
            if (pinV[pin] > 255):
                pinV[pin] = 255
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin]/1000)
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
        sleep(pinDelay[pin]/1000)
    PWMLock.release()


def core1_village_houses():
    print("hello")
second_thread = _thread.start_new_thread(core1_village_houses, ())
def loop():
    global fr
    global sT
    global max_count
    global pinInt
    while True:
        PWMLock.acquire()
        if PWMLock.locked():
            while fr < max_count:
                fr = fr + 100
                for x in pinInt:
                    pins[x].duty_u16(fr)
                    x = x + 1
                sleep(sT)
            while fr > 0:
                fr = fr - 100
                for x in pinInt:
                    pins[x].duty_u16(fr)
                    x = x + 1
                sleep(sT)
            PWMLock.release()
setup1()
#loop()
second_thread = _thread.start_new_thread(loop, ())