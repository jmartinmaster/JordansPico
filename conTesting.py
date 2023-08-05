from machine import Pin,PWM
from time import sleep
import _thread, random
#This runs PIO from Core1 outputting PWM to Pin(25)
#leaving core0 to do other stuffs. Thread for core1 can 
#be loaded to run several things as State machine runs at 0.1MHz
#and Pico core is at 125MHz
#This alows for PWM output on unused core without interupting main, Core0

pins = [3, 5, 6, 4, 9, 10, 11]
ground = 12
pinV = [0, 0, 0, 255, 255, 255, 255]
pinFV= [random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10), random.randint(5, 10)]
pinDelay= [random.randint(50, 70), random.randint(50, 70), random.randint(50, 70), random.randint(50, 70), random.randint(50, 70), random.randint(50, 70), random.randint(50, 70)]

pins[0] = PWM(Pin(3))
pins[1] = PWM(Pin(5))
pins[2] = PWM(Pin(6))
pins[3] = PWM(Pin(4))
pins[4] = PWM(Pin(9))
pins[5] = PWM(Pin(10))
pins[6] = PWM(Pin(11))
def core1_village_houses():
    print("hello")

second_thread = _thread.start_new_thread(core1_village_houses, ())