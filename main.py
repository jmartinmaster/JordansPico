from shared_functions import wait_for_completion
import _thread
from core1_activities import loop, core1_task
from time import sleep

# Function to read from REPL and update values
def repl_input_handler():
    global max_counts, increment_value, decrement_value, sT
    while True:
        command = input("Enter command: ")
        if command.startswith("max_count"):
            parts = command.split()
            if len(parts) == 3:
                pin = int(parts[1])
                value = int(parts[2])
                max_counts[pin] = value
        elif command.startswith("increment"):
            value = int(command.split()[1])
            increment_value = value
        elif command.startswith("decrement"):
            value = int(command.split()[1])
            decrement_value = value
        elif command.startswith("speed"):
            value = float(command.split()[1])
            sT = value

# Start the loop and core1 task in new threads
_thread.start_new_thread(core1_task, ())
sleep(0.5)
_thread.start_new_thread(loop, ())

# Start the REPL input handler in cor
# 
repl_input_handler()

while True:
    wait_for_completion()
    sleep(0.001)
