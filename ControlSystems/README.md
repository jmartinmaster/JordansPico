# RP2040 Control Studio Starter

This starter app gives you a desktop control panel for a MicroPython RP2040 board using a CustomTkinter interface and a serial REPL transport.

## What it does

- Lists serial ports, probes them with a quick verification pass, and classifies the connected device when possible.
- Runs serial-port refresh in the background so device discovery does not block the editor.
- Keeps project settings in an MVC structure.
- Lets you define editable live parameters on the desktop side.
- Generates a complete board runtime script into the on-screen editor.
- Uses IDLE colorizer components for Python syntax highlighting inside the editor.
- Shows line numbers in the editor gutter for easier navigation to reported errors.
- Adds indentation-aware editing for Enter, Tab, Shift+Tab, and smart backspace.
- Uploads the edited runtime script to the board over raw REPL.
- Sends live parameter updates without re-uploading the whole script.
- Runs and stops a board-side test routine.
- Shows a board information panel for the selected serial device.
- Includes a multiline console input for sending raw MicroPython snippets.
- Adds an interrupt button for stopping the current board-side program.
- Keeps console command history with previous/next recall.
- Lets you run the current editor selection directly on the connected board.
- Lets you open and save files from this computer and browse/open/save files on the board.
- Adds a navigable board directory tree with lazy loading so the browser behaves more like Thonny on MicroPython boards.
- Adds save-current and run-current actions for the active editor script.
- Uploads and reloads the current runtime automatically before `Run Test`, so the test uses the active runtime module and current parameter values even if the editor is temporarily showing another board file.
- Handles terminal `Ctrl+C` cleanly when the desktop app is launched from a shell.
- Adds right-click context menus on the editor and console text areas.
- Makes the whole left sidebar scrollable so project, files, and parameter controls stay reachable.
- Saves reusable project definitions into `ControlSystems/projects`.
- Detects whether the connected board is exposing a friendly `main.py` command prompt (`Enter command:`), a normal friendly MicroPython prompt (`>>>`), or a raw-REPL-capable runtime.

## Layout

- `run_control_panel.py`: application entry point.
- `app/models.py`: project and parameter models.
- `app/controller.py`: UI actions and serial orchestration.
- `app/view.py`: CustomTkinter desktop UI.
- `app/serial_service.py`: MicroPython raw REPL file transfer and command execution.
- `app/runtime_templates.py`: generated starter board script.

## Install

On Debian or Ubuntu, install the Tk bindings first:

```bash
sudo apt-get install -y python3-tk
```

Then create a local environment and install the app dependencies:

```bash
cd /home/jamie/Documents/Github/JordansPico/ControlSystems
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## Run

```bash
cd /home/jamie/Documents/Github/JordansPico/ControlSystems
.venv/bin/python run_control_panel.py
```

## Workflow

1. Plug in the RP2040 running MicroPython.
2. Click `Refresh Ports`, review the verified device labels in the port list, then choose the board port and connect.
3. Edit the parameter list.
4. Click `Generate Script` to rebuild the runtime template if needed.
5. Edit the generated runtime code in the center editor.
6. Click `Upload Runtime` to copy that script to the board and import it.
7. Change parameter values and click `Apply Live Values` to see updates immediately.
8. Click `Run Test` to upload the current runtime, apply the current parameter values, and execute the board routine.

## Notes

- Live updates depend on the uploaded runtime module still exposing `set_params`, `run_test`, `stop_test`, and `status`. Opening another board file in the editor does not replace the cached runtime used by `Upload Runtime` and `Run Test` unless the editor content is itself a runtime script.
- The starter board script is intentionally small and can be rewritten for your own actuators, sensors, or PWM logic.
- The raw REPL transport writes the runtime as `<module_name>.py` on the board filesystem.
- Board file browsing now follows Thonny's immediate-child listing model instead of recursively walking the whole filesystem at refresh time.
- Port verification uses a lightweight serial open plus passive read or newline ping. It avoids a hard REPL interrupt during discovery, but some USB serial devices may still expose limited metadata only.
- Raw REPL entry now retries through noisy startup output so a crashing `main.py` is less likely to block uploads or console execution.
- If your board is running the repo root `main.py` command loop, set `Runtime Module Name` to `main`. In this mode the app uses friendly REPL commands instead of uploading `control_runtime.py`.
- If the app detects the board is already sitting at the repo root `main.py` prompt, it will switch the runtime module name to `main` automatically.
- Live REPL mode currently maps parameters named `speed`, `increment`, `decrement`, `max_count_<pin>`, and `max_count[<pin>]` to the command syntax expected by the repo root `main.py`.