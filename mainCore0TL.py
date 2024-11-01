from machine import Pin, PWM
from time import sleep
import _thread

# Set up PWM pins and locks
pins = [PWM(Pin(3)), PWM(Pin(5)), PWM(Pin(6)), PWM(Pin(4)), PWM(Pin(9)), PWM(Pin(10)), PWM(Pin(11)), PWM(Pin(25))]
pinV = [0, 0, 0, 255, 255, 255, 255, 255]
pinFV = [10, 10, 10, 10, 10, 10, 10, 10]
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.002, 0.002, 0.002, 0.002]
sT = 0.001
fr = 0
max_count = 65530
pin = 7
value = 65530

slock = _thread.allocate_lock()
thread_complete = False

def setup_pins():
    for p in pins:
        p.freq(10000)
        p.duty_u16(65530)

def pin_fade_up():
    global pins, pinV, pinFV, pin, value, slock, thread_complete
    while slock.locked():
        sleep(0.001)
    slock.acquire()
    while pinV[pin] < value:
        pinV[pin] = min(pinV[pin] + pinFV[pin], 65530)
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin])
    slock.release()
    thread_complete = True  # Signal task completion

def pin_fade_down():
    global pins, pinV, pinFV, pin, value, slock, thread_complete
    while slock.locked():
        sleep(0.001)
    slock.acquire()
    while pinV[pin] > value:
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
        while fr < max_count:
            fr += 100
            pins[7].duty_u16(fr)
            sleep(sT)
        while fr > 0:
            fr -= 100
            pins[7].duty_u16(fr)
            sleep(sT)
        slock.release()
        thread_complete = True  # Signal task completion

setup_pins()

def wait_for_completion():
    global thread_complete
    while not thread_complete:
        sleep(0.001)
    thread_complete = False

pin = 7
value = 65530
_thread.start_new_thread(pin_fade_up, ())
wait_for_completion()

value = 0
_thread.start_new_thread(pin_fade_down, ())
wait_for_completion()

value = 20000
_thread.start_new_thread(pin_fade_up, ())
wait_for_completion()

value = 40000
_thread.start_new_thread(pin_fade_down, ())
wait_for_completion()

_thread.start_new_thread(loop, ())
