from machine import Pin, PWM
from time import sleep
import _thread
import random
from spi_screen import setup_display, draw_text  # Import your display functions

# Set up PWM pins and locks
pins = [PWM(Pin(25)), PWM(Pin(28)), PWM(Pin(16)), PWM(Pin(17)), PWM(Pin(18)), PWM(Pin(19)), PWM(Pin(13)), PWM(Pin(24))]  
button_pins = [Pin(12, Pin.IN, Pin.PULL_UP), Pin(13, Pin.IN, Pin.PULL_UP), Pin(14, Pin.IN, Pin.PULL_UP), Pin(15, Pin.IN, Pin.PULL_UP)]
pinV = [0, 0, 0, 255, 255, 255, 255, 255]
pinFV = [10, 10, 10, 10, 10, 10, 10, 10]
pinDelay = [0.001, 0.002, 0.001, 0.002, 0.002, 0.002, 0.002, 0.002]
fr = [0] * len(pins)
max_counts = [65500] * len(pins)  # Array to hold max_count values for each pin
sT = 0.001

slock = _thread.allocate_lock()
thread_complete = False
toggle_state = False  # State variable for the toggled pin
toggle_pin = 0  # Index of the pin to be toggled

tft = setup_display()  # Initialize the display

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
    thread_complete = True

def core1_task():
    pass

_thread.start_new_thread(core1_task, ())

def loop():
    global fr, max_counts, sT, pins, slock, thread_complete, toggle_state, toggle_pin
    direction = [1] * len(pins)  # Direction array for each pin
    while True:
        while slock.locked():
            sleep(0.001)
        slock.acquire()
        
        # Toggle pin state
        if toggle_state:
            pins[toggle_pin].duty_u16(65535)
        else:
            pins[toggle_pin].duty_u16(0)
        toggle_state = not toggle_state
        
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

            pins[i].duty_u16(fr[i])
            sleep(sT)

            # Display current status on the screen
            draw_text(tft, f"Pin {i}: {fr[i]}", 10, 10 * i)
        
        slock.release()
        thread_complete = True  # Signal task completion

def dynamic_max_count_calculation(pin_index):
    return random.randint(10, 65500)  # Generate a random max_count value for the pin

def read_buttons():
    global max_counts, sT
    while True:
        if not button_pins[0].value():
            max_counts = [mc + 5000 for mc in max_counts]  # Increase max_count
        if not button_pins[1].value():
            max_counts = [mc - 5000 for mc in max_counts]  # Decrease max_count
        if not button_pins[2].value():
            sT = max(0.0001, sT - 0.0001)  # Increase speed
        if not button_pins[3].value():
            sT = min(0.01, sT + 0.0001)  # Decrease speed
        sleep(0.1)

setup_pins()

def wait_for_completion():
    global thread_complete
    while not thread_complete:
        sleep(0.001)
    thread_complete = False

# Start the loop and button reading in new threads
_thread.start_new_thread(loop, ())
_thread.start_new_thread(read_buttons, ())

while True:
    wait_for_completion()
    sleep(0.001)
