from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep
import random

# Define the PIO assembler code for PWM
@asm_pio(sideset_init=PIO.OUT_LOW)
def pwm():
    pull(noblock)          .side(0)
    mov(x, osr)            .side(0)
    mov(y, osr)            .side(0)
    label("on")
    jmp(y_dec, "off")      .side(1)
    jmp(x_dec, "on")       .side(0)
    label("off")
    nop()                  .side(0)

# Initialize the PIO state machines
sm = StateMachine(0, pwm, freq=20000, sideset_base=Pin(25))
sm1 = StateMachine(1, pwm, freq=20000, sideset_base=Pin(28))
# Add more state machines for other pins as needed...

pinV = [0, 0, 0, 255, 255, 255, 255, 255]
max_counts = [65500] * len(pinV)
sT = 0.01
increment_value = 300
decrement_value = 300
toggle_state = False
toggle_pin = 0

def core1_task():
    print("Core1 task running")

def loop():
    global pinV, max_counts, sT, toggle_state, toggle_pin, increment_value, decrement_value
    direction = [1] * len(pinV)
    while True:
        for i in range(len(pinV) - 1):
            max_counts[i] = dynamic_max_count_calculation(i)
            if direction[i] == 1:
                if pinV[i] < max_counts[i]:
                    pinV[i] += increment_value
                else:
                    direction[i] = -1
            else:
                if pinV[i] > 0:
                    pinV[i] -= decrement_value
                else:
                    direction[i] = 1

            # Send duty cycle to PIO state machine
            if i == 0:
                sm.put(pinV[i])
            elif i == 1:
                sm1.put(pinV[i])
            # Add more cases for other state machines...

            sleep(sT)

        # Toggle pin state
        if toggle_state:
            sm1.put(65535)
        else:
            sm1.put(0)
        toggle_state = not toggle_state

def dynamic_max_count_calculation(pin_index):
    return random.randint(10, 65500)

def setup_pins():
    sm.active(1)
    sm1.active(1)
    # Activate other state machines as needed...

setup_pins()
