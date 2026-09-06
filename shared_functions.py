import threading
from time import sleep

# Shared event for coordinating updates between the REPL thread and worker code.
event = threading.Event()
thread_complete = False

def wait_for_completion():
    global thread_complete
    while not thread_complete:
        sleep(0.001)
    thread_complete = False

def pin_fade(pin, target_value, pins, pinV, pinFV, pinDelay):
    global thread_complete
    event.wait()
    while pinV[pin] != target_value:
        if pinV[pin] < target_value:
            pinV[pin] = min(pinV[pin] + pinFV[pin], 65530)
        else:
            pinV[pin] = max(pinV[pin] - pinFV[pin], 0)
        pins[pin].duty_u16(pinV[pin])
        sleep(pinDelay[pin])
    thread_complete = True
    event.clear()
