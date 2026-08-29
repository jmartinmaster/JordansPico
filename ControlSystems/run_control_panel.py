from signal import signal
from pathlib import Path

from app import ControlPanelController, ControlPanelView


def main() -> None:
    interrupt_requested = {"value": False}

    def handle_sigint(_signum, _frame) -> None:
        interrupt_requested["value"] = True

    base_dir = Path(__file__).resolve().parent
    controller = ControlPanelController(base_dir)
    view = ControlPanelView(controller)
    controller.attach_view(view)
    controller.bootstrap()

    signal(2, handle_sigint)

    def poll_for_terminal_interrupt() -> None:
        if interrupt_requested["value"]:
            try:
                view.log("Terminal Ctrl+C received. Closing control studio.")
            finally:
                view.destroy()
            return
        view.after(150, poll_for_terminal_interrupt)

    view.after(150, poll_for_terminal_interrupt)
    view.mainloop()


if __name__ == "__main__":
    main()