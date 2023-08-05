# Example of using PIO for PWM, and fading the brightness of an LED
# for a more wrapped-up examples, see https://github.com/raspberrypi/pico-micropython-examples/blob/master/pio/pio_pwm.py

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep

@asm_pio(sideset_init=PIO.OUT_LOW)
def pwm_prog():
    pull(noblock) .side(0)
    mov(x, osr) # Keep most recent pull data stashed in X, for recycling by noblock
    mov(y, isr) # ISR must be preloaded with PWM count max
    label("pwmloop")
    jmp(x_not_y, "skip")
    nop()         .side(1)
    label("skip")
    jmp(y_dec, "pwmloop")
    

pwm_sm = StateMachine(0, pwm_prog, freq=10000000, sideset_base=Pin(25))

pwm_sm.put(max_count)
pwm_sm.exec("pull()")
pwm_sm.exec("mov(isr, osr)")
pwm_sm.active(1)

while True:
    while True:
        cycle = cycle - 1
        while x < max_count:
            x = x + 10
            pwm_sm.put(x)
            sleep(sT)
        while x > 0:
            x = x - 10
            pwm_sm.put(x)
            sleep(sT)