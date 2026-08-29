from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from .models import ControlProject, ParameterDefinition, default_parameters
from .runtime_templates import build_runtime_script, default_board_logic
from .serial_service import MicroPythonSerialService, SerialTransportError


class ControlPanelController:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.projects_dir = base_dir / "projects"
        self.service = MicroPythonSerialService()
        self.view = None
        self._port_lookup: dict[str, str] = {}
        self._port_details: dict[str, object] = {}
        self._current_local_file: Path | None = None
        self._current_board_file: str = ""
        self._runtime_script_cache = ""
        self._busy = False
        self._refreshing = False

    def attach_view(self, view) -> None:
        self.view = view

    def bootstrap(self) -> None:
        project = ControlProject(parameters=default_parameters(), script_text=default_board_logic())
        project.script_text = build_runtime_script(project)
        self._runtime_script_cache = project.script_text
        self.view.load_project(project)
        self.refresh_ports()
        self._update_saved_projects()
        self.view.log("Starter project loaded.")

    def refresh_ports(self) -> None:
        if self._refreshing:
            self.view.log("A serial port refresh is already in progress.")
            return

        def action() -> None:
            discovered_ports = self.service.list_ports()
            ports = [port for port in discovered_ports if port.verified]
            labels = [port.label for port in ports]
            self._port_lookup = {port.label: port.device for port in ports}
            self._port_details = {port.device: port for port in ports}
            self.view.set_ports(labels)
            self.view.set_status(f"Detected {len(labels)} verified serial port(s).")
            if ports:
                for port in ports:
                    self.view.log(f"{port.label}: {port.detail_line}")
                self.update_selected_port_info(labels[0])
            else:
                self.view.set_board_info(None)
                hidden_count = len(discovered_ports)
                if hidden_count:
                    self.view.log(f"No verified serial ports were detected. {hidden_count} unverified port(s) were hidden.")
                else:
                    self.view.log("No serial ports were detected during refresh.")

        self._run_refresh_background(action)

    def update_selected_port_info(self, selected_label: str) -> None:
        if selected_label == "No serial ports detected":
            self.view.set_board_info(None)
            return
        device = self._port_lookup.get(selected_label, selected_label)
        self.view.set_board_info(self._port_details.get(device))

    def connect(self) -> None:
        payload = self.view.collect_project_state()
        selected_label = payload["port"]
        if selected_label == "No serial ports detected":
            self.view.log("No serial ports are available. Connect the RP2040 and refresh the list.")
            self.view.set_status("No serial ports available.")
            return
        port = self._port_lookup.get(selected_label, selected_label)
        baud_rate = int(payload["baud_rate"])

        def action() -> None:
            self.service.connect(port, baud_rate)
            self.view.set_connected(True, port)
            runtime_mode = self.service.runtime_mode
            if runtime_mode == "friendly-main":
                self.view.set_module_name("main")
                self.view.log("Detected friendly main.py command prompt. Switched runtime module name to main.")
            elif runtime_mode == "friendly-python":
                self.view.log("Detected friendly MicroPython REPL prompt.")
            elif runtime_mode == "raw-repl":
                self.view.log("Detected raw REPL capable runtime.")
            self.view.log(f"Connected to {port} at {baud_rate} baud.")
            self.view.set_status(f"Connected to {port} ({runtime_mode}).")

        self._run_background(action)

    def disconnect(self) -> None:
        self.service.disconnect()
        self.view.set_connected(False, "")
        self.view.log("Disconnected from board.")
        self.view.set_status("Disconnected.")

    def run_console_command(self, command: str) -> None:
        cleaned = command.strip()
        if not cleaned:
            return

        project = self._project_from_view(include_current_editor=False)

        def action() -> None:
            self.view.log(f">>> {cleaned}")
            if self._uses_live_repl_protocol(project):
                stdout, stderr = self.service.execute_friendly_command(cleaned, timeout=6.0)
            else:
                stdout, stderr = self.service.execute(cleaned + "\n", timeout=6.0)
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Console command executed.")

        self._run_background(action)

    def run_selected_code(self) -> None:
        selection = self.view.get_editor_selection().strip()
        if not selection:
            self.view.log("Select code in the editor before using Run Selection.")
            return
        self.run_console_command(selection)

    def interrupt_console(self) -> None:
        def action() -> None:
            stdout, stderr = self.service.interrupt_current_program()
            self.view.log("KeyboardInterrupt sent to board.")
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Interrupt sent.")

        self._run_background(action)

    def generate_script(self) -> None:
        project = self._project_from_view(include_current_editor=False)
        script = build_runtime_script(project)
        self._runtime_script_cache = script
        self.view.set_script_text(script)
        self.view.log("Generated runtime script from current parameters.")
        self.view.set_status("Editor updated from parameter model.")

    def save_project(self) -> None:
        project = self._project_from_view(include_current_editor=True)
        target = self.projects_dir / f"{project.project_name}.json"
        project.save(target)
        self.view.log(f"Saved project to {target.name}.")
        self._update_saved_projects()
        self.view.set_status(f"Saved {project.project_name}.")

    def load_project(self, project_name: str) -> None:
        target = self.projects_dir / f"{project_name}.json"
        project = ControlProject.load(target)
        self._runtime_script_cache = project.script_text
        self.view.load_project(project)
        self._current_local_file = None
        self.view.log(f"Loaded project {project_name}.")
        self.view.set_status(f"Loaded {project_name}.")

    def save_current_script(self) -> None:
        if self._current_board_file:
            self.save_board_file()
            return
        self.save_local_file()

    def run_current_script(self) -> None:
        remote_path = self._current_board_file or self.view.get_selected_board_file().strip()
        script_text = self.view.get_script_text()

        def action() -> None:
            if remote_path:
                self.service.write_file(remote_path, script_text)
                stdout, stderr = self.service.run_board_file(remote_path)
                self._current_board_file = remote_path
                self.view.set_current_file_labels(
                    local_path=str(self._current_local_file) if self._current_local_file else "",
                    board_path=self._current_board_file,
                )
                self.view.log(f"Saved and ran board file {remote_path}.")
            else:
                stdout, stderr = self.service.execute(script_text, timeout=15.0)
                self.view.log("Ran current editor buffer directly on the board.")
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Current script run finished.")

        self._run_background(action)

    def open_local_file(self) -> None:
        selected_path = self.view.ask_open_path(
            title="Open Local Python File",
            filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not selected_path:
            return
        self._capture_runtime_from_editor()
        path = Path(selected_path)
        content = path.read_text(encoding="utf-8")
        self.view.set_script_text(content)
        self._current_local_file = path
        self.view.set_current_file_labels(local_path=str(path), board_path=self._current_board_file)
        self.view.log(f"Opened local file {path.name}.")
        self.view.set_status(f"Loaded {path.name} from this computer.")

    def save_local_file(self) -> None:
        target = self._current_local_file
        if target is None:
            chosen = self.view.ask_save_path(
                title="Save Local Python File",
                defaultextension=".py",
                filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")],
            )
            if not chosen:
                return
            target = Path(chosen)

        target.write_text(self.view.get_script_text(), encoding="utf-8")
        self._current_local_file = target
        self.view.set_current_file_labels(local_path=str(target), board_path=self._current_board_file)
        self.view.log(f"Saved local file {target.name}.")
        self.view.set_status(f"Saved {target.name} to this computer.")

    def refresh_board_files(self) -> None:
        def action() -> None:
            tree = self.service.list_board_directory("")
            self.view.set_board_tree(tree)
            self.view.set_current_file_labels(
                local_path=str(self._current_local_file) if self._current_local_file else "",
                board_path=self._current_board_file,
            )
            self.view.log("Board directory tree refreshed.")
            self.view.set_status("Board file list refreshed.")

        self._run_background(action)

    def load_board_directory(self, directory: str) -> None:
        def action() -> None:
            children = self.service.list_board_directory(directory)
            self.view.set_board_tree_children(directory, children)
            self.view.set_status(f"Loaded {directory or '/'}.")

        self._run_background(action)

    def open_board_file(self) -> None:
        remote_path = self.view.get_selected_board_file().strip()
        if not remote_path:
            self.view.log("Select or enter a board file path before opening it.")
            return

        self._capture_runtime_from_editor()

        def action() -> None:
            content = self.service.read_board_file(remote_path)
            self._current_board_file = remote_path
            self.view.set_script_text(content)
            self.view.set_current_file_labels(
                local_path=str(self._current_local_file) if self._current_local_file else "",
                board_path=self._current_board_file,
            )
            self.view.log(f"Opened board file {remote_path}.")
            self.view.set_status(f"Loaded {remote_path} from board.")

        self._run_background(action)

    def save_board_file(self) -> None:
        remote_path = self.view.get_selected_board_file().strip() or self._current_board_file
        if not remote_path:
            self.view.log("Select or enter a board file path before saving it.")
            return

        content = self.view.get_script_text()

        def action() -> None:
            self.service.write_file(remote_path, content)
            self._current_board_file = remote_path
            self.view.set_current_file_labels(
                local_path=str(self._current_local_file) if self._current_local_file else "",
                board_path=self._current_board_file,
            )
            self.view.log(f"Saved editor contents to board file {remote_path}.")
            self.view.set_status(f"Saved {remote_path} to board.")

        self._run_background(action)

    def select_board_tree_path(self, board_path: str, is_dir: bool) -> None:
        if is_dir:
            self.view.set_current_file_labels(
                local_path=str(self._current_local_file) if self._current_local_file else "",
                board_path=board_path,
            )
            return
        self._current_board_file = board_path
        self.view.set_current_file_labels(
            local_path=str(self._current_local_file) if self._current_local_file else "",
            board_path=self._current_board_file,
        )

    def push_runtime(self) -> None:
        project = self._project_from_view(include_current_editor=False)
        if self._uses_live_repl_protocol(project):
            self.view.log("Live REPL mode uses the board's existing main.py. Upload Runtime was skipped to avoid overwriting it.")
            self.view.set_status("Upload Runtime skipped in live REPL mode.")
            return
        project.script_text = self._resolve_runtime_script(project)
        remote_file_name = f"{project.module_name}.py"

        def action() -> None:
            self.service.write_file(remote_file_name, project.script_text)
            stdout, stderr = self.service.load_runtime_module(project.module_name)
            self._log_serial_result(stdout, stderr)
            self.view.set_status(f"Uploaded {remote_file_name} and reloaded runtime.")

        self._run_background(action)

    def apply_live_values(self) -> None:
        project = self._project_from_view(include_current_editor=True)
        parameters = project.parameter_mapping()

        def action() -> None:
            if self._uses_live_repl_protocol(project):
                commands, skipped = self._build_live_repl_commands(parameters)
                for command in commands:
                    self.view.log(f">>> {command}")
                    stdout, stderr = self.service.execute_friendly_command(command, timeout=4.0)
                    self._log_serial_result(stdout, stderr)
                if skipped:
                    self.view.log("Skipped unsupported live parameters: " + ", ".join(skipped))
                if not commands:
                    self.view.log("No live REPL parameter mappings were found.")
                self.view.set_status("Applied live REPL parameter update.")
                return

            stdout, stderr = self.service.set_parameters(project.module_name, parameters)
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Applied live parameter update.")

        self._run_background(action)

    def run_test(self) -> None:
        project = self._project_from_view(include_current_editor=False)
        if not self._uses_live_repl_protocol(project):
            project.script_text = self._resolve_runtime_script(project)
        remote_file_name = f"{project.module_name}.py"
        parameters = project.parameter_mapping()

        def action() -> None:
            if self._uses_live_repl_protocol(project):
                commands, skipped = self._build_live_repl_commands(parameters)
                for command in commands:
                    self.view.log(f">>> {command}")
                    stdout, stderr = self.service.execute_friendly_command(command, timeout=4.0)
                    self._log_serial_result(stdout, stderr)
                if skipped:
                    self.view.log("Skipped unsupported live parameters: " + ", ".join(skipped))
                self.view.log("Updated live REPL runtime through main.py command input.")
                self.view.set_status("Live REPL runtime updated.")
                return

            self.service.write_file(remote_file_name, project.script_text)
            load_stdout, load_stderr = self.service.load_runtime_module(project.module_name)
            apply_stdout, apply_stderr = self.service.set_parameters(project.module_name, parameters)
            stdout, stderr = self.service.run_test(project.module_name)
            self._log_serial_result(load_stdout, load_stderr)
            self._log_serial_result(apply_stdout, apply_stderr)
            self._log_serial_result(stdout, stderr)
            self.view.log(f"Uploaded and ran {remote_file_name} with current parameters.")
            self.view.set_status("Board test run finished.")

        self._run_background(action)

    def stop_test(self) -> None:
        project = self._project_from_view(include_current_editor=True)

        def action() -> None:
            if self._uses_live_repl_protocol(project):
                self.view.log("Live REPL mode has no stop_test() hook. Use Interrupt to break the current board program.")
                self.view.set_status("Use Interrupt for live REPL mode.")
                return
            stdout, stderr = self.service.stop_test(project.module_name)
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Stop command sent.")

        self._run_background(action)

    def read_status(self) -> None:
        project = self._project_from_view(include_current_editor=True)

        def action() -> None:
            if self._uses_live_repl_protocol(project):
                self.view.log("Live REPL mode does not expose runtime status(). Use the console or board output from main.py.")
                self.view.set_status("Live REPL mode has no status() hook.")
                return
            stdout, stderr = self.service.read_status(project.module_name)
            self._log_serial_result(stdout, stderr)
            self.view.set_status("Runtime status refreshed.")

        self._run_background(action)

    def _project_from_view(self, include_current_editor: bool) -> ControlProject:
        payload = self.view.collect_project_state()
        parameters = [ParameterDefinition(**item) for item in payload["parameters"]]
        script_text = payload["script_text"] if include_current_editor else default_board_logic()
        return ControlProject(
            project_name=payload["project_name"],
            module_name=payload["module_name"],
            port=payload["port"],
            baud_rate=int(payload["baud_rate"]),
            parameters=parameters,
            script_text=script_text,
        )

    def _capture_runtime_from_editor(self) -> None:
        current_text = self.view.get_script_text()
        if self._is_valid_runtime_script(current_text):
            self._runtime_script_cache = current_text

    def _resolve_runtime_script(self, project: ControlProject) -> str:
        current_text = self.view.get_script_text()
        if self._is_valid_runtime_script(current_text):
            self._runtime_script_cache = current_text
            return current_text
        if self._is_valid_runtime_script(self._runtime_script_cache):
            return self._runtime_script_cache

        generated = build_runtime_script(project)
        self._runtime_script_cache = generated
        return generated

    def _looks_like_runtime_script(self, script_text: str) -> bool:
        required_fragments = (
            "def set_param(",
            "def set_params(",
            "def run_test(",
            "def stop_test(",
            "def status(",
        )
        return all(fragment in script_text for fragment in required_fragments)

    def _is_valid_runtime_script(self, script_text: str) -> bool:
        if not self._looks_like_runtime_script(script_text):
            return False
        try:
            compile(script_text, "control_runtime.py", "exec")
        except SyntaxError:
            return False
        return True

    def _uses_live_repl_protocol(self, project: ControlProject) -> bool:
        return project.module_name.strip().lower() == "main" or self.service.runtime_mode == "friendly-main"

    def _build_live_repl_commands(self, parameters: dict[str, object]) -> tuple[list[str], list[str]]:
        commands: list[str] = []
        skipped: list[str] = []
        for name, value in parameters.items():
            command = self._map_live_repl_parameter(name, value)
            if command is None:
                skipped.append(name)
                continue
            commands.append(command)
        return commands, skipped

    def _map_live_repl_parameter(self, name: str, value: object) -> str | None:
        normalized = name.strip()
        lowered = normalized.lower()
        if lowered in {"speed", "increment", "decrement"}:
            return f"{lowered} {value}"
        if lowered.startswith("max_count_"):
            pin = normalized[len("max_count_"):].strip()
            if pin.isdigit():
                return f"max_count {pin} {value}"
            return None
        if lowered.startswith("max_count[") and normalized.endswith("]"):
            pin = normalized[normalized.find("[") + 1:-1].strip()
            if pin.isdigit():
                return f"max_count {pin} {value}"
            return None
        return None

    def _update_saved_projects(self) -> None:
        project_names = sorted(path.stem for path in self.projects_dir.glob("*.json"))
        self.view.set_saved_projects(project_names)

    def _run_background(self, action: Callable[[], None]) -> None:
        if self._busy:
            self.view.log("A board operation is already running.")
            return

        def worker() -> None:
            self._busy = True
            self.view.set_busy(True)
            try:
                action()
            except (OSError, ValueError, SerialTransportError) as exc:
                self.view.log(f"Operation failed: {exc}")
                self.view.set_status(str(exc))
            finally:
                self._busy = False
                self.view.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _run_refresh_background(self, action: Callable[[], None]) -> None:
        def worker() -> None:
            self._refreshing = True
            self.view.set_refreshing(True)
            try:
                action()
            except (OSError, ValueError, SerialTransportError) as exc:
                self.view.log(f"Refresh failed: {exc}")
                self.view.set_status(str(exc))
            finally:
                self._refreshing = False
                self.view.set_refreshing(False)

        threading.Thread(target=worker, daemon=True).start()

    def _log_serial_result(self, stdout: str, stderr: str) -> None:
        if stdout.strip():
            self.view.log(stdout.strip())
        if stderr.strip():
            self.view.log(f"stderr: {stderr.strip()}")
