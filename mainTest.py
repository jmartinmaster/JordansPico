from machine import Pin,PWM
from time import sleep
import _thread, random
#This runs PIO from Core1 outputting PWM to Pin(25)
#leaving core0 to do other stuffs. Thread for core1 can 
#be loaded to run several things as State machine runs at 0.1MHz
#and Pico core is at 125MHz
#This alows for PWM output on unused core without interupting main, Core0

max_count = 65530
pins = [3, 5, 6, 4, 9, 10, 11, 25]
ground = 12
pinV = [0, 0, 0, 65530, 65530, 65530, 65530, 65530]
pinFV= [random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10)]
pinDelay= [random.randint(50, 70)/1000, random.randint(50, 70)/1000, random.randint(50, 70)/1000, random.randint(50, 70)/1000, random.randint(50, 70)/1000, random.randint(50, 70)/1000, random.randint(50, 70)/1000]
sT = 0.001
fr = 0

pins[0] = PWM(Pin(3))
pins[1] = PWM(Pin(5))
pins[2] = PWM(Pin(6))
pins[3] = PWM(Pin(4))
pins[4] = PWM(Pin(9))
pins[5] = PWM(Pin(10))
pins[6] = PWM(Pin(11))
pins[7] = PWM(Pin(25))
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

def pinFader( pin, value):
    global pins
    global pinV
    global pinFV
    global pinDelay
    global max_count
    if (pinV[pin] < value):
        while (pinV[pin] < value):
            pinV[pin] = pinV[pin] + pinFV[pin]
            if (pinV[pin] > max_count):
                pinV[pin] = max_count
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin])

    if (pinV[pin] > value):
        while (pinV[pin] > value):
            pinV[pin] = pinV[pin] - pinFV[pin]
        if (pinV[pin] < 0 ):
            pinV[pin] = 0
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin])


#core1 unable to use veriables from main without passing them back and forth
def core1_village_houses():
    print("hello")
second_thread = _thread.start_new_thread(core1_village_houses, ())
def loop():
    global fr
    global sT
    pinFader(7, 65530)
    pinFader(7, 0)
setup1()
#loop()
second_thread = _thread.start_new_thread(loop, ())