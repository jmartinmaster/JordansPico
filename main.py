<<<<<<< HEAD
from shared_functions import wait_for_completion
import _thread
from core1_activities import loop, core1_task
=======
from shared_functions import wait_for_completion, event  # Import event from shared_functions
import _thread, threading
from core1_activities import core1_main, core1_task, update_interval, print_flag
>>>>>>> 77753c2dce3653b92bfd0b30d048ff4fa09778e6
from time import sleep

# Function to read from REPL and update values
def repl_input_handler():
<<<<<<< HEAD
    global max_counts, increment_value, decrement_value, sT
=======
    global max_counts, increment_value, decrement_value, sT, trigger_core1_task, update_interval, print_flag
>>>>>>> 77753c2dce3653b92bfd0b30d048ff4fa09778e6
    while True:
        command = input("Enter command: ")
        if command.startswith("max_count"):
            parts = command.split()
            if len(parts) == 3:
                pin = int(parts[1])
                value = int(parts[2])
                max_counts[pin] = value
<<<<<<< HEAD
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
=======
                event.set()  # Signal that the value has been updated
        elif command.startswith("increment"):
            value = int(command.split()[1])
            increment_value = value
            event.set()  # Signal that the value has been updated
        elif command.startswith("decrement"):
            value = int(command.split()[1])
            decrement_value = value
            event.set()  # Signal that the value has been updated
        elif command.startswith("speed"):
            value = float(command.split()[1])
            update_interval = value
            print_flag = True
            event.set()  # Signal that the value has been updated

# Function to wait for the event and perform tasks
def event_handler():
    while True:
        event.wait()  # Wait for the event to be set
        # Perform tasks that need to be done after the event is set
        event.clear()  # Clear the event

# Start the event handler thread
_thread.start_new_thread(event_handler, ())

# Start the REPL input handler
repl_input_handler()
>>>>>>> 77753c2dce3653b92bfd0b30d048ff4fa09778e6

# Start the REPL input handler in cor
# 
repl_input_handler()

while True:
    wait_for_completion()
<<<<<<< HEAD
    sleep(0.001)
=======
    sleep(0.001)
>>>>>>> 77753c2dce3653b92bfd0b30d048ff4fa09778e6
