# Example of using PIO for PWM, and fading the brightness of an LED
# for a more wrapped-up examples, see https://github.com/raspberrypi/pico-micropython-examples/blob/master/pio/pio_pwm.py

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep
max_count=225

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
pwm_sm2 = StateMachine(1, pwm_prog, freq=10000000, sideset_base=Pin(28))
pwm_sm3 = StateMachine(2, pwm_prog, freq=10000000, sideset_base=Pin(24))

pwm_sm.put(max_count)
pwm_sm.exec("pull()")
pwm_sm.exec("mov(isr, osr)")
pwm_sm.active(1)
pwm_sm2.put(max_count)
pwm_sm2.exec("pull()")
pwm_sm2.exec("mov(isr, osr)")
pwm_sm2.active(1)
pwm_sm3.put(max_count)
pwm_sm3.exec("pull()")
pwm_sm3.exec("mov(isr, osr)")
pwm_sm3.active(1)
x = 0
sT = 0.05
while True:
    while True:
        while x < max_count:
            x = x + 10
            pwm_sm.put(x)
            sleep(sT)
            pwm_sm2.put(x+20)
            sleep(sT)
            pwm_sm3.put(x+30)
            sleep(sT)
        while x > 0:
            x = x - 10
            pwm_sm.put(x)
            x = x - 20
            sleep(sT)
            pwm_sm2.put(x)
            x = x - 30            
            sleep(sT)
            pwm_sm3.put(x)
            sleep(sT)