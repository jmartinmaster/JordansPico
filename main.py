from machine import Pin,PWM
from time import sleep
import _thread, random
#This runs PIO from Core1 outputting PWM to Pin(25)
#leaving core0 to do other stuffs. Thread for core1 can 
#be loaded to run several things as State machine runs at 0.1MHz
#and Pico core is at 125MHz
#This allows for PWM output on unused core without interrupting main, Core0

#########Board is SparkFun RP2040 Core on SparkFun ATP Carrier#############################

pins = [25, 28, 16, 17, 18, 19, 13,24 ]
pinInt = [0,1,2,3,4,5,6,7]
ground = 12
pinV = [0, 0, 0, 255, 255, 255, 255, 255]
pinFV= [random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10)]
pinDelay= [random.randint(80, 120)/1000, random.randint(80, 120)/1000,random.randint(80, 120)/1000,random.randint(80, 120)/1000,random.randint(80, 120)/1000,random.randint(80, 120)/1000,random.randint(80, 120)/1000,]
sT = 0.001
fr = 0
max_count = 65530
pin = 0
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

def pinFader():
    global pins
    global pinV
    global pinFV
    global pin
    global value
    if (pinV[pin] < value):
        while (pinV[pin] < value):
            pinV[pin] = pinV[pin] + pinFV[pin]
            if (pinV[pin] > 255):
                pinV[pin] = 255
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin]/1000)

    if (pinV[pin] > value):
        while (pinV[pin] > value):
            pinV[pin] = pinV[pin] - pinFV[pin]
        if (pinV[pin] < 0 ):
            pinV[pin] = 0
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin]/1000)


#core1 unable to use variables from main without passing them back and forth
def core1_village_houses():
    print("hello")
second_thread = _thread.start_new_thread(core1_village_houses, ())
def loop():
    global fr
    global sT
    global max_count
    global pinInt
    while True:
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
setup1()
#loop()
second_thread = _thread.start_new_thread(loop, ())