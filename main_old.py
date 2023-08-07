from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep
import _thread
import pio_debouncer

### duplicate of old main file for backup###


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
    
max_count = 500
sT = 0.04
cycles = 10
#sT controls the delay before the next value is sent to the StateMachine
def core1_thread():
    #input the number of times to run the thing
    cycle = cycles
    x = 0
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
def handler(sm):
    print("Here")
button = pio_debouncer.DebouncerLowPIO(0,0,handler)

#100,000Hz seems to be fine, too much higher causes problems with sleep()
#and seems to get twitchy. Might be able to use to utime.sleep_us()
pwm_sm = StateMachine(4, pwm_prog, freq=100000, sideset_base=Pin(25))
pwm_sm.put(max_count)
pwm_sm.exec("pull()")
pwm_sm.exec("mov(isr, osr)")
pwm_sm.active(1)


#Start of tasks for Core0 all _thread.start trigger on Core1
second_thread = _thread.start_new_thread(core1_thread, ())
