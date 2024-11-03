from machine import Pin, PWM  # Importing Pin and PWM classes from the machine module
from time import sleep  # Importing sleep function from the time module
import _thread  # Importing _thread module for threading support
import random  # Importing random module for generating random numbers

# Set up PWM pins and locks
pins = [PWM(Pin(3)), PWM(Pin(5)), PWM(Pin(6)), PWM(Pin(4)), PWM(Pin(9)), PWM(Pin(10)), PWM(Pin(11)), PWM(Pin(25))]
pinV = [0, 0, 0, 255, 255, 255, 255, 255]  # Initial PWM values for each pin
pinFV = [10, 10, 10, 10, 10, 10, 10, 10]  # Fixed increment/decrement values for PWM
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.002, 0.002, 0.002, 0.002]  # Delay values for PWM updates
fr = [0] * len(pins)  # Array to store PWM frequency values for each pin
max_counts = [65500] * len(pins)  # Array to hold max_count values for each pin
sT = 0.001  # Sleep time for PWM updates

slock = _thread.allocate_lock()  # Create a lock for synchronizing threads
thread_complete = False  # Flag to indicate thread completion

def setup_pins():
    for p in pins:
        p.freq(10000)  # Set frequency for all PWM pins
        p.duty_u16(65530)  # Set initial duty cycle for all PWM pins

def pin_fade(pin, target_value):
    global pins, pinV, pinFV, slock, thread_complete
    while slock.locked():
        sleep(0.001)  # Wait if the lock is acquired by another thread
    slock.acquire()  # Acquire the lock
    while pinV[pin] != target_value:
        if pinV[pin] < target_value:
            pinV[pin] = min(pinV[pin] + pinFV[pin], 65530)
        else:
            pinV[pin] = max(pinV[pin] - pinFV[pin], 0)
        pins[pin].duty_u16(pinV[pin])  # Update duty cycle for the pin
        sleep(pinDelay[pin])  # Wait before the next update
    slock.release()  # Release the lock
    thread_complete = True  # Signal thread completion

def core1_task():
    pass  # Placeholder function for tasks running on the second core

_thread.start_new_thread(core1_task, ())  # Start the core1_task in a new thread

def loop():
    global fr, max_counts, sT, pins, slock, thread_complete
    direction = [1] * len(pins)  # Direction array for each pin (1 for increasing, -1 for decreasing)
    while True:
        while slock.locked():
            sleep(0.001)  # Wait if the lock is acquired by another thread
        slock.acquire()  # Acquire the lock
        for i in range(len(pins) - 1):
            max_counts[i] = dynamic_max_count_calculation(i)  # Update max_count dynamically
            if direction[i] == 1:  # Increasing
                if fr[i] < max_counts[i]:
                    fr[i] += 100
                else:
                    direction[i] = -1
            else:  # Decreasing
                if fr[i] > 0:
                    fr[i] -= 100
                else:
                    direction[i] = 1
            pins[i].duty_u16(fr[i])  # Update duty cycle for the pin
            sleep(sT)  # Wait before the next update
        slock.release()  # Release the lock
        thread_complete = True  # Signal thread completion

def dynamic_max_count_calculation(pin_index):
    return random.randint(10, 65500)  # Generate a random max_count value for the pin

setup_pins()  # Set up PWM pins

def wait_for_completion():
    global thread_complete
    while not thread_complete:
        sleep(0.001)  # Wait for the thread to complete
    thread_complete = False

_thread.start_new_thread(loop, ())  # Start the loop in a new thread

while True:
    wait_for_completion()  # Wait for the loop thread to complete
    sleep(0.001)  # Continue waiting
