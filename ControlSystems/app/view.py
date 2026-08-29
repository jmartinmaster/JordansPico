from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

import customtkinter as ctk

from .editor import PythonEditor
from .models import ControlProject, VALUE_TYPES, default_parameters
from .serial_service import BoardFileNode, SerialPortInfo


class ParameterRow:
    def __init__(self, master, remove_callback) -> None:
        self.frame = ctk.CTkFrame(master, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=2)
        self.frame.grid_columnconfigure(1, weight=3)
        self.frame.grid_columnconfigure(2, weight=0)

        self.name_entry = ctk.CTkEntry(self.frame, placeholder_text="name")
        self.type_menu = ctk.CTkOptionMenu(self.frame, values=list(VALUE_TYPES), width=92)
        self.value_entry = ctk.CTkEntry(self.frame, placeholder_text="value")
        self.remove_button = ctk.CTkButton(self.frame, text="Remove", width=82, command=lambda: remove_callback(self))

        self.name_entry.grid(row=0, column=0, columnspan=3, padx=0, pady=(4, 2), sticky="ew")
        self.type_menu.grid(row=1, column=0, padx=(0, 8), pady=(2, 6), sticky="ew")
        self.value_entry.grid(row=1, column=1, padx=(0, 8), pady=(2, 6), sticky="ew")
        self.remove_button.grid(row=1, column=2, pady=(2, 6), sticky="e")

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def destroy(self) -> None:
        self.frame.destroy()

    def set_data(self, name: str, value_type: str, raw_value: str) -> None:
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)
        self.type_menu.set(value_type)
        self.value_entry.delete(0, "end")
        self.value_entry.insert(0, raw_value)

    def get_data(self) -> dict[str, str]:
        return {
            "name": self.name_entry.get().strip() or "parameter",
            "value_type": self.type_menu.get(),
            "raw_value": self.value_entry.get(),
        }


class ControlPanelView(ctk.CTk):
    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.parameter_rows: list[ParameterRow] = []
        self.port_values: list[str] = []
        self.saved_projects: list[str] = []
        self.console_history: list[str] = []
        self.console_history_index: int = 0
        self._board_tree_index: dict[str, dict[str, object]] = {}

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("RP2040 Control Studio")
        self.geometry("1560x940")
        self.minsize(1320, 820)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_left_panel()
        self._build_editor_panel()
        self._build_console_panel()

    def _build_top_bar(self) -> None:
        top = ctk.CTkFrame(self, corner_radius=0, height=72)
        top.grid(row=0, column=0, columnspan=3, sticky="nsew")
        top.grid_columnconfigure(0, weight=2)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=1)
        top.grid_columnconfigure(3, weight=1)
        top.grid_columnconfigure(4, weight=1)
        top.grid_columnconfigure(5, weight=1)

        self.port_menu = ctk.CTkOptionMenu(top, values=["No serial ports detected"])
        self.baud_entry = ctk.CTkEntry(top)
        self.baud_entry.insert(0, "115200")
        self.refresh_button = ctk.CTkButton(top, text="Refresh Ports", command=self.controller.refresh_ports)
        self.connect_button = ctk.CTkButton(top, text="Connect", command=self.controller.connect)
        self.disconnect_button = ctk.CTkButton(top, text="Disconnect", command=self.controller.disconnect)
        self.status_label = ctk.CTkLabel(top, text="Ready", anchor="w")
        self.port_menu.configure(command=self.controller.update_selected_port_info)

        ctk.CTkLabel(top, text="Serial Port", anchor="w").grid(row=0, column=0, padx=(20, 8), pady=(12, 2), sticky="sw")
        ctk.CTkLabel(top, text="Baud", anchor="w").grid(row=0, column=1, padx=8, pady=(12, 2), sticky="sw")
        self.port_menu.grid(row=1, column=0, padx=(20, 8), pady=(0, 14), sticky="ew")
        self.baud_entry.grid(row=1, column=1, padx=8, pady=(0, 14), sticky="ew")
        self.refresh_button.grid(row=1, column=2, padx=8, pady=(0, 14), sticky="ew")
        self.connect_button.grid(row=1, column=3, padx=8, pady=(0, 14), sticky="ew")
        self.disconnect_button.grid(row=1, column=4, padx=8, pady=(0, 14), sticky="ew")
        self.status_label.grid(row=1, column=5, padx=(8, 20), pady=(0, 14), sticky="ew")

    def _build_left_panel(self) -> None:
        left = ctk.CTkFrame(self, corner_radius=18)
        left.grid(row=1, column=0, padx=(20, 10), pady=(18, 20), sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        left_content = ctk.CTkScrollableFrame(left, fg_color="transparent")
        left_content.grid(row=0, column=0, sticky="nsew")
        left_content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_content, text="Project", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(18, 10), sticky="w"
        )

        self.project_name_entry = ctk.CTkEntry(left_content, placeholder_text="project_name")
        self.module_name_entry = ctk.CTkEntry(left_content, placeholder_text="control_runtime")
        self.saved_projects_menu = ctk.CTkOptionMenu(left_content, values=["No saved projects"])
        self.load_project_button = ctk.CTkButton(left_content, text="Load Saved Project", command=self._load_selected_project)
        self.save_button = ctk.CTkButton(left_content, text="Save Project", command=self.controller.save_project)
        self.generate_button = ctk.CTkButton(left_content, text="Generate Script", command=self.controller.generate_script)
        self.add_parameter_button = ctk.CTkButton(left_content, text="Add Parameter", command=self.add_parameter_row)
        self.open_local_button = ctk.CTkButton(left_content, text="Open Local File", command=self.controller.open_local_file)
        self.save_local_button = ctk.CTkButton(left_content, text="Save Local File", command=self.controller.save_local_file)
        self.refresh_board_files_button = ctk.CTkButton(left_content, text="Refresh Board Files", command=self.controller.refresh_board_files)
        self.open_board_button = ctk.CTkButton(left_content, text="Open Board File", command=self.controller.open_board_file)
        self.save_board_button = ctk.CTkButton(left_content, text="Save To Board File", command=self.controller.save_board_file)
        self.current_local_label = ctk.CTkLabel(left_content, text="Local: none", anchor="w", wraplength=260, justify="left")
        self.current_board_label = ctk.CTkLabel(left_content, text="Board: none", anchor="w", wraplength=260, justify="left")

        ctk.CTkLabel(left_content, text="Project Name").grid(row=1, column=0, padx=18, pady=(4, 4), sticky="w")
        self.project_name_entry.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(left_content, text="Runtime Module Name").grid(row=3, column=0, padx=18, pady=(4, 4), sticky="w")
        self.module_name_entry.grid(row=4, column=0, padx=18, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(left_content, text="Saved Projects").grid(row=5, column=0, padx=18, pady=(4, 4), sticky="w")
        self.saved_projects_menu.grid(row=6, column=0, padx=18, pady=(0, 10), sticky="ew")
        self.load_project_button.grid(row=7, column=0, padx=18, pady=(0, 10), sticky="new")
        self.save_button.grid(row=8, column=0, padx=18, pady=6, sticky="ew")
        self.generate_button.grid(row=9, column=0, padx=18, pady=6, sticky="ew")
        self.add_parameter_button.grid(row=10, column=0, padx=18, pady=(6, 10), sticky="ew")
        ctk.CTkLabel(left_content, text="Files", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=11, column=0, padx=18, pady=(8, 6), sticky="w"
        )
        self.open_local_button.grid(row=12, column=0, padx=18, pady=4, sticky="ew")
        self.save_local_button.grid(row=13, column=0, padx=18, pady=4, sticky="ew")
        self.refresh_board_files_button.grid(row=14, column=0, padx=18, pady=(8, 4), sticky="ew")
        self.board_tree_frame = ctk.CTkFrame(left_content, fg_color="transparent")
        self.board_tree_frame.grid(row=15, column=0, padx=18, pady=4, sticky="nsew")
        self.board_tree_frame.grid_columnconfigure(0, weight=1)
        self.board_tree_frame.grid_rowconfigure(0, weight=1)
        self.board_tree = ttk.Treeview(self.board_tree_frame, show="tree", height=8)
        self.board_tree.grid(row=0, column=0, sticky="nsew")
        self.board_tree_scroll = ttk.Scrollbar(self.board_tree_frame, orient="vertical", command=self.board_tree.yview)
        self.board_tree_scroll.grid(row=0, column=1, sticky="ns")
        self.board_tree.configure(yscrollcommand=self.board_tree_scroll.set)
        self.board_tree.bind("<<TreeviewSelect>>", self._on_board_tree_selected)
        self.board_tree.bind("<Double-1>", self._on_board_tree_double_click)
        self.board_tree.bind("<<TreeviewOpen>>", self._on_board_tree_open)
        self.open_board_button.grid(row=16, column=0, padx=18, pady=4, sticky="ew")
        self.save_board_button.grid(row=17, column=0, padx=18, pady=4, sticky="ew")
        self.current_local_label.grid(row=18, column=0, padx=18, pady=(8, 2), sticky="ew")
        self.current_board_label.grid(row=19, column=0, padx=18, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(left_content, text="Parameters", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=20, column=0, padx=18, pady=(10, 6), sticky="w"
        )
        self.parameters_frame = ctk.CTkScrollableFrame(left_content, height=320)
        self.parameters_frame.grid(row=21, column=0, padx=18, pady=(0, 18), sticky="nsew")
        self.parameters_frame.grid_columnconfigure(0, weight=1)

    def _build_editor_panel(self) -> None:
        editor = ctk.CTkFrame(self, corner_radius=18)
        editor.grid(row=1, column=1, padx=10, pady=(18, 20), sticky="nsew")
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(1, weight=1)
        editor.grid_rowconfigure(3, weight=0)

        ctk.CTkLabel(editor, text="Board Runtime Script", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(18, 10), sticky="w"
        )
        self.script_textbox = PythonEditor(editor)
        self.script_textbox.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="nsew")

        actions = ctk.CTkFrame(editor, fg_color="transparent")
        actions.grid(row=2, column=0, padx=18, pady=(0, 18), sticky="ew")
        for column in range(5):
            actions.grid_columnconfigure(column, weight=1)

        self.upload_button = ctk.CTkButton(actions, text="Upload Runtime", command=self.controller.push_runtime)
        self.apply_button = ctk.CTkButton(actions, text="Apply Live Values", command=self.controller.apply_live_values)
        self.status_button = ctk.CTkButton(actions, text="Read Status", command=self.controller.read_status)
        self.run_button = ctk.CTkButton(actions, text="Run Test", command=self.controller.run_test)
        self.stop_button = ctk.CTkButton(actions, text="Stop Test", command=self.controller.stop_test)
        self.run_selection_button = ctk.CTkButton(actions, text="Run Selection", command=self.controller.run_selected_code)
        self.save_current_button = ctk.CTkButton(actions, text="Save Current", command=self.controller.save_current_script)
        self.run_current_button = ctk.CTkButton(actions, text="Run Current", command=self.controller.run_current_script)

        self.upload_button.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.apply_button.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self.status_button.grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        self.run_button.grid(row=0, column=3, padx=6, pady=6, sticky="ew")
        self.stop_button.grid(row=0, column=4, padx=6, pady=6, sticky="ew")
        self.run_selection_button.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="ew")
        self.save_current_button.grid(row=1, column=1, columnspan=2, padx=6, pady=(0, 6), sticky="ew")
        self.run_current_button.grid(row=1, column=3, columnspan=2, padx=6, pady=(0, 6), sticky="ew")

    def _build_console_panel(self) -> None:
        panel = ctk.CTkFrame(self, corner_radius=18)
        panel.grid(row=1, column=2, padx=(10, 20), pady=(18, 20), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=0)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(panel, text="Board Info", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(18, 10), sticky="w"
        )
        self.board_info_textbox = ctk.CTkTextbox(panel, height=180, font=("Fira Code", 13), wrap="word")
        self.board_info_textbox.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="ew")
        self.board_info_textbox.insert("end", "No port selected.\n")
        self.board_info_textbox.configure(state="disabled")

        ctk.CTkLabel(panel, text="Console", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=2, column=0, padx=18, pady=(0, 10), sticky="w"
        )
        self.console_textbox = ctk.CTkTextbox(panel, font=("Fira Code", 14))
        self.console_textbox.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="nsew")
        self.console_textbox.insert("end", "Control studio ready.\n")
        self.console_textbox.configure(state="disabled")
        self._install_text_context_menu(self.console_textbox._textbox, include_cut=False)

        console_input = ctk.CTkFrame(panel, fg_color="transparent")
        console_input.grid(row=4, column=0, padx=18, pady=(0, 18), sticky="ew")
        console_input.grid_columnconfigure(0, weight=1)

        self.console_entry = ctk.CTkTextbox(console_input, height=120, font=("Fira Code", 13), wrap="word")
        self.console_entry.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky="ew")
        self.console_entry.insert("1.0", "print('hello from MicroPython')\n")
        self._install_text_context_menu(self.console_entry._textbox, include_cut=True)

        self.console_send_button = ctk.CTkButton(console_input, text="Run Buffer", width=110, command=self._submit_console_command)
        self.console_interrupt_button = ctk.CTkButton(console_input, text="Interrupt", width=110, command=self.controller.interrupt_console)
        self.console_clear_button = ctk.CTkButton(console_input, text="Clear Input", width=110, command=self._clear_console_input)
        self.console_history_prev_button = ctk.CTkButton(console_input, text="Prev", width=90, command=self._show_previous_history)
        self.console_history_next_button = ctk.CTkButton(console_input, text="Next", width=90, command=self._show_next_history)
        self.console_send_button.grid(row=1, column=0, padx=(0, 10), sticky="w")
        self.console_interrupt_button.grid(row=1, column=1, padx=(0, 10), sticky="w")
        self.console_clear_button.grid(row=1, column=2, padx=(0, 10), sticky="w")
        self.console_history_prev_button.grid(row=1, column=3, padx=(0, 10), sticky="w")
        self.console_history_next_button.grid(row=1, column=4, sticky="w")
        self.console_entry._textbox.bind("<Control-Up>", lambda _event: self._show_previous_history())
        self.console_entry._textbox.bind("<Control-Down>", lambda _event: self._show_next_history())

    def set_ports(self, ports: list[str]) -> None:
        self.after(0, lambda: self._update_ports(ports))

    def _update_ports(self, ports: list[str]) -> None:
        previous_selection = self.port_menu.get()
        self.port_values = ports or ["No serial ports detected"]
        self.port_menu.configure(values=self.port_values)
        next_selection = previous_selection if previous_selection in self.port_values else self.port_values[0]
        self.port_menu.set(next_selection)

    def set_saved_projects(self, project_names: list[str]) -> None:
        self.after(0, lambda: self._update_saved_projects(project_names))

    def _update_saved_projects(self, project_names: list[str]) -> None:
        self.saved_projects = project_names or ["No saved projects"]
        self.saved_projects_menu.configure(values=self.saved_projects)
        self.saved_projects_menu.set(self.saved_projects[0])

    def set_board_tree(self, board_nodes: list[BoardFileNode]) -> None:
        self.after(0, lambda: self._update_board_tree(board_nodes))

    def _update_board_tree(self, board_nodes: list[BoardFileNode]) -> None:
        self._board_tree_index.clear()
        for item in self.board_tree.get_children():
            self.board_tree.delete(item)

        if not board_nodes:
            placeholder = self.board_tree.insert("", "end", text="No board files")
            self._board_tree_index[placeholder] = {"path": "", "is_dir": False, "loaded": True}
            return

        for node in board_nodes:
            self._insert_board_tree_node("", node)

    def set_board_tree_children(self, parent_path: str, board_nodes: list[BoardFileNode]) -> None:
        self.after(0, lambda: self._update_board_tree_children(parent_path, board_nodes))

    def _update_board_tree_children(self, parent_path: str, board_nodes: list[BoardFileNode]) -> None:
        item_id = self._find_tree_item_by_path(parent_path)
        if not item_id:
            return
        for child_id in self.board_tree.get_children(item_id):
            self._remove_tree_metadata(child_id)
            self.board_tree.delete(child_id)
        for node in board_nodes:
            self._insert_board_tree_node(item_id, node)
        self._board_tree_index[item_id]["loaded"] = True

    def _insert_board_tree_node(self, parent: str, node: BoardFileNode) -> None:
        label = node.name + ("/" if node.is_dir else "")
        item_id = self.board_tree.insert(parent, "end", text=label, open=False)
        self._board_tree_index[item_id] = {"path": node.path, "is_dir": node.is_dir, "loaded": False}
        if node.is_dir:
            placeholder_id = self.board_tree.insert(item_id, "end", text="Loading...")
            self._board_tree_index[placeholder_id] = {"path": "", "is_dir": False, "loaded": True}

    def get_selected_board_file(self) -> str:
        selection = self.board_tree.selection()
        if not selection:
            return ""
        item_info = self._board_tree_index.get(selection[0], {"path": "", "is_dir": False})
        board_path = str(item_info.get("path", ""))
        is_dir = bool(item_info.get("is_dir", False))
        return "" if is_dir else board_path

    def set_current_file_labels(self, local_path: str, board_path: str) -> None:
        self.after(0, lambda: self._update_current_file_labels(local_path, board_path))

    def _update_current_file_labels(self, local_path: str, board_path: str) -> None:
        self.current_local_label.configure(text=f"Local: {local_path or 'none'}")
        self.current_board_label.configure(text=f"Board: {board_path or 'none'}")

    def add_parameter_row(self, parameter: dict[str, str] | None = None) -> None:
        row = ParameterRow(self.parameters_frame, self.remove_parameter_row)
        row.grid(row=len(self.parameter_rows), column=0, sticky="ew")
        seed = parameter or {"name": "parameter", "value_type": "str", "raw_value": ""}
        row.set_data(seed["name"], seed["value_type"], seed["raw_value"])
        self.parameter_rows.append(row)

    def remove_parameter_row(self, row: ParameterRow) -> None:
        self.parameter_rows.remove(row)
        row.destroy()
        for index, item in enumerate(self.parameter_rows):
            item.frame.grid_configure(row=index)

    def collect_project_state(self) -> dict[str, object]:
        return {
            "project_name": self.project_name_entry.get().strip() or "rp2040_starter",
            "module_name": self.module_name_entry.get().strip() or "control_runtime",
            "port": self.port_menu.get(),
            "baud_rate": self.baud_entry.get().strip() or "115200",
            "parameters": [row.get_data() for row in self.parameter_rows],
            "script_text": self.script_textbox.get("1.0", "end").strip() + "\n",
        }

    def load_project(self, project: ControlProject) -> None:
        self.project_name_entry.delete(0, "end")
        self.project_name_entry.insert(0, project.project_name)
        self.module_name_entry.delete(0, "end")
        self.module_name_entry.insert(0, project.module_name)
        self.baud_entry.delete(0, "end")
        self.baud_entry.insert(0, str(project.baud_rate))
        for row in list(self.parameter_rows):
            self.remove_parameter_row(row)
        rows = project.parameters or default_parameters()
        for item in rows:
            self.add_parameter_row(item.to_dict())
        script_text = project.script_text.strip()
        if "def set_param" not in script_text:
            from .runtime_templates import build_runtime_script

            script_text = build_runtime_script(project)
        self.set_script_text(script_text)

    def set_script_text(self, script_text: str) -> None:
        self.after(0, lambda: self.script_textbox.replace_all_text(script_text))

    def set_module_name(self, module_name: str) -> None:
        self.after(0, lambda: self._update_module_name(module_name))

    def _update_module_name(self, module_name: str) -> None:
        self.module_name_entry.delete(0, "end")
        self.module_name_entry.insert(0, module_name)

    def get_script_text(self) -> str:
        return self.script_textbox.get("1.0", "end").rstrip() + "\n"

    def get_editor_selection(self) -> str:
        return self.script_textbox.get_selected_text()

    def set_board_info(self, port_info: SerialPortInfo | None) -> None:
        self.after(0, lambda: self._update_board_info(port_info))

    def _update_board_info(self, port_info: SerialPortInfo | None) -> None:
        self.board_info_textbox.configure(state="normal")
        self.board_info_textbox.delete("1.0", "end")
        if port_info is None:
            self.board_info_textbox.insert("end", "No port selected.\n")
        else:
            lines = [
                f"Port: {port_info.device}",
                f"Detected Device: {port_info.detected_device}",
                f"Verified: {'yes' if port_info.verified else 'no'}",
                f"Probe State: {port_info.probe_state}",
                f"Probe Summary: {port_info.probe_summary}",
                f"Description: {port_info.description or 'Unknown'}",
                f"Manufacturer: {port_info.manufacturer or 'Unknown'}",
                f"Product: {port_info.product or 'Unknown'}",
                f"Hardware ID: {port_info.hardware_id or 'Unknown'}",
                f"Response Preview: {port_info.response_preview or 'None'}",
            ]
            self.board_info_textbox.insert("end", "\n".join(lines) + "\n")
        self.board_info_textbox.configure(state="disabled")

    def log(self, message: str) -> None:
        self.after(0, self._append_log, message)

    def _append_log(self, message: str) -> None:
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", message.rstrip() + "\n")
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    def set_status(self, message: str) -> None:
        self.after(0, lambda: self.status_label.configure(text=message))

    def set_connected(self, is_connected: bool, port: str) -> None:
        text = f"Connected: {port}" if is_connected else "Disconnected"
        self.set_status(text)

    def set_busy(self, busy: bool) -> None:
        self.after(0, lambda: self._toggle_busy(busy))

    def set_refreshing(self, refreshing: bool) -> None:
        self.after(0, lambda: self.refresh_button.configure(state="disabled" if refreshing else "normal"))

    def _toggle_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        widgets = [
            self.refresh_button,
            self.connect_button,
            self.disconnect_button,
            self.load_project_button,
            self.save_button,
            self.generate_button,
            self.add_parameter_button,
            self.upload_button,
            self.apply_button,
            self.status_button,
            self.run_button,
            self.stop_button,
            self.run_selection_button,
            self.save_current_button,
            self.run_current_button,
            self.console_send_button,
            self.console_interrupt_button,
            self.console_clear_button,
            self.console_history_prev_button,
            self.console_history_next_button,
            self.open_local_button,
            self.save_local_button,
            self.refresh_board_files_button,
            self.open_board_button,
            self.save_board_button,
        ]
        for widget in widgets:
            widget.configure(state=state)
        self.console_entry.configure(state=state)
        self.board_tree.configure(selectmode="browse" if state == "normal" else "none")

    def _load_selected_project(self) -> None:
        project_name = self.saved_projects_menu.get()
        if project_name == "No saved projects":
            self.log("No saved projects are available yet.")
            return
        self.controller.load_project(project_name)

    def _submit_console_command(self) -> None:
        command = self.console_entry.get("1.0", "end").strip()
        if not command:
            return
        self.console_history.append(command)
        self.console_history_index = len(self.console_history)
        self.controller.run_console_command(command)

    def _clear_console_input(self) -> None:
        self.console_entry.delete("1.0", "end")

    def _show_previous_history(self):
        if not self.console_history:
            return "break"
        self.console_history_index = max(0, self.console_history_index - 1)
        self._load_history_item(self.console_history[self.console_history_index])
        return "break"

    def _show_next_history(self):
        if not self.console_history:
            return "break"
        self.console_history_index = min(len(self.console_history), self.console_history_index + 1)
        if self.console_history_index == len(self.console_history):
            self._clear_console_input()
        else:
            self._load_history_item(self.console_history[self.console_history_index])
        return "break"

    def _load_history_item(self, command: str) -> None:
        self.console_entry.delete("1.0", "end")
        self.console_entry.insert("1.0", command)

    def _on_board_tree_selected(self, _event=None) -> None:
        selection = self.board_tree.selection()
        if not selection:
            return
        item_info = self._board_tree_index.get(selection[0], {"path": "", "is_dir": False})
        board_path = str(item_info.get("path", ""))
        is_dir = bool(item_info.get("is_dir", False))
        self.controller.select_board_tree_path(board_path, is_dir)

    def _on_board_tree_double_click(self, _event=None) -> None:
        selection = self.board_tree.selection()
        if not selection:
            return
        item_info = self._board_tree_index.get(selection[0], {"path": "", "is_dir": False})
        board_path = str(item_info.get("path", ""))
        is_dir = bool(item_info.get("is_dir", False))
        if not is_dir and board_path:
            self.controller.open_board_file()

    def _on_board_tree_open(self, _event=None) -> None:
        item_id = self.board_tree.focus()
        if not item_id:
            return
        item_info = self._board_tree_index.get(item_id, {"path": "", "is_dir": False, "loaded": True})
        if not bool(item_info.get("is_dir", False)) or bool(item_info.get("loaded", True)):
            return
        board_path = str(item_info.get("path", ""))
        self.controller.load_board_directory(board_path)

    def _find_tree_item_by_path(self, board_path: str) -> str:
        for item_id, item_info in self._board_tree_index.items():
            if item_info.get("path") == board_path:
                return item_id
        return ""

    def _remove_tree_metadata(self, item_id: str) -> None:
        for child_id in self.board_tree.get_children(item_id):
            self._remove_tree_metadata(child_id)
        self._board_tree_index.pop(item_id, None)

    def ask_open_path(self, title: str, filetypes):
        return filedialog.askopenfilename(parent=self, title=title, filetypes=filetypes)

    def ask_save_path(self, title: str, defaultextension: str, filetypes):
        return filedialog.asksaveasfilename(
            parent=self,
            title=title,
            defaultextension=defaultextension,
            filetypes=filetypes,
        )

    def _install_text_context_menu(self, widget: tk.Text, include_cut: bool) -> None:
        menu = tk.Menu(widget, tearoff=False)
        if include_cut:
            menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))
        widget.bind("<Button-3>", lambda event: self._show_context_menu(event, menu), add=True)

    @staticmethod
    def _show_context_menu(event, menu: tk.Menu) -> str:
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        return "break"