from machine import Pin, PWM
from rp2 import PIO, StateMachine, asm_pio
from time import sleep
import random
from shared_functions import event  # Import event from shared_functions

# Define PWM pins
pins = [PWM(Pin(25)), PWM(Pin(28)), PWM(Pin(16)), PWM(Pin(17)), PWM(Pin(18)), PWM(Pin(19)), PWM(Pin(13)), PWM(Pin(24))]

# Array to hold PWM values
array = [0] * len(pins)
buffer_address = id(array)  # Address of the array

@asm_pio()
def read_array():
    pull(noblock)
    mov(x, osr)
    mov(y, x)
    mov(isr, y)
    irq(noblock, 0)

@asm_pio(sideset_init=PIO.OUT_LOW, out_init=(PIO.OUT_LOW,) * 8, autopull=True, pull_thresh=32)
def write_to_pins():
    wrap_target()
    pull(block)
    out(pins, 32)  # Output the value to pins
    wrap()

# Set frequency to 2000 Hz for both state machines
sm0 = StateMachine(0, read_array, freq=2000)
sm1 = StateMachine(1, write_to_pins, freq=2000, sideset_base=Pin(25), out_base=Pin(25))

sm0.put(buffer_address)
sm0.active(1)
sm1.active(1)

# Define update_interval globally
update_interval = 0.5  # Default update interval in seconds

def core1_task():
    global array
    for i in range(len(array)):
        array[i] = random.randint(0, 65535)  # Simpler and efficient solution

def core1_main():
    global array, update_interval
    direction = [1] * len(array)
    while True:
        event.wait()  # Wait for the event to be set
        for i in range(len(array)):
            if direction[i] == 1:
                if array[i] < 65535:
                    array[i] += 500
                else:
                    direction[i] = -1
            else:
                if array[i] > 0:
                    array[i] -= 500
                else:
                    direction[i] = 1

            sm0.put(array[i])
            sm1.put(array[i])  # Send the value to PIO1 for writing to pins
        
        sleep(update_interval)  # Delay before updating the array values again
        event.clear()  # Clear the event

def setup_pins():
    for pin in pins:
        pin.freq(10000)  # Set the PWM frequency
    # Activate state machines for further use

setup_pins()