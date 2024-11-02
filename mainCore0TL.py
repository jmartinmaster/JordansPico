from machine import Pin, PWM
from time import sleep
import _thread

# Set up PWM pins and locks
pins = [PWM(Pin(3)), PWM(Pin(5)), PWM(Pin(6)), PWM(Pin(4)), PWM(Pin(9)), PWM(Pin(10)), PWM(Pin(11)), PWM(Pin(25))]
pinV = [0, 0, 0, 255, 255, 255, 255, 255]
pinFV = [10, 10, 10, 10, 10, 10, 10, 10]
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.002, 0.002, 0.002, 0.002]
fr = [0] * len(pins)
max_count = 65530
sT = 0.001
value = 65530

slock = _thread.allocate_lock()
thread_complete = False

def setup_pins():
    for p in pins:
        p.freq(10000)
        p.duty_u16(65530)

def pin_fade(pin, target_value):
    global pins, pinV, pinFV, slock, thread_complete
    while slock.locked():
        sleep(0.001)
    slock.acquire()
    while pinV[pin] != target_value:
        if pinV[pin] < target_value:
            pinV[pin] = min(pinV[pin] + pinFV[pin], 65530)
        else:
            pinV[pin] = max(pinV[pin] - pinFV[pin], 0)
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin])
    slock.release()
    thread_complete = True  # Signal task completion

def core1_task():
    print("hello from core1")

_thread.start_new_thread(core1_task, ())

def loop():
    global fr, max_count, sT, pins, slock, thread_complete
    print("Loop started")
    while True:
        while slock.locked():
            sleep(0.001)
        slock.acquire()
        for i in range(len(pins) - 1):
            if fr[i] < max_count:
                fr[i] += 100
            else:
                fr[i] -= 100
            pins[i].duty_u16(fr[i])
            sleep(sT)
        slock.release()
        thread_complete = True  # Signal task completion


setup_pins() 

def wait_for_completion(): 
    global thread_complete 
    while not thread_complete: 
        sleep(0.001) 
    thread_complete = False 
    
wait_for_completion() 

_thread.start_new_thread(loop, ())

while True:
    sleep(0.001)
