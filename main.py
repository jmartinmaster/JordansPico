from machine import Pin, PWM # type: ignore
from time import sleep # type: ignore
import _thread # type: ignore

# Set up PWM pins and locks
pins = [PWM(Pin(25)), PWM(Pin(28)), PWM(Pin(16)), PWM(Pin(17)), PWM(Pin(18)), PWM(Pin(19)), PWM(Pin(13)), PWM(Pin(24))] 
pinV = [0, 0, 0, 255, 255, 255, 255, 255]
pinFV = [10, 10, 10, 10, 10, 10, 10, 10]
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.002, 0.002, 0.002, 0.002]
fr = [0] * len(pins)
max_count = 65500
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
    print("Pin fade started")
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
    thread_complete = True
    print("Pin fade complete.")

def core1_task():
    print("hello from core1")

_thread.start_new_thread(core1_task, ())

def loop():
    global fr, max_count, sT, pins, slock, thread_complete
    print("Loop started")
    direction = 1  # 1 for up, -1 for down
    while True:
        while slock.locked():
            sleep(0.0001)
        slock.acquire()
        for i in range(len(pins) - 1):
            if direction == 1:  # Increasing
                if fr[i] < max_count:
                    fr[i] += 900
                else:
                    direction = -1
            else:  # Decreasing
                if fr[i] > 0:
                    fr[i] -= 900
                else:
                    direction = 1

            pins[i].duty_u16(fr[i])
            print(f"Pin {i} fr value: {fr[i]}")
            sleep(sT)

        print(f"Loop iteration complete, i={i}")
        slock.release()
        thread_complete = True  # Signal task completion


setup_pins()

def wait_for_completion():
    global thread_complete
    while not thread_complete:
        sleep(0.001)
    thread_complete = False

# Start the loop in a new thread
_thread.start_new_thread(loop, ())

while True:
    wait_for_completion()
    # Do other tasks or just keep waiting
    sleep(0.001)
