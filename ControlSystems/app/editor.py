from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
try:
    from idlelib.colorizer import ColorDelegator
    from idlelib.percolator import Percolator
except ModuleNotFoundError:
    ColorDelegator = None
    Percolator = None


DEDENT_TOKENS = ("return", "break", "continue", "pass", "raise")


class PythonEditor(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.line_numbers = tk.Text(
            self,
            width=5,
            padx=8,
            pady=14,
            takefocus=0,
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            state="disabled",
            cursor="arrow",
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        self.text_widget = tk.Text(
            self,
            wrap="none",
            undo=True,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.text_widget.grid(row=0, column=1, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self._on_scrollbar)
        self.scrollbar.grid(row=0, column=2, sticky="ns")

        self._font = tkfont.Font(font=self.text_widget.cget("font"))
        self._background = "#1f1f1f"
        self._foreground = "#f3f4f6"
        self._gutter_background = "#18181b"
        self._gutter_foreground = "#71717a"
        self.text_widget.configure(
            padx=14,
            pady=14,
            insertwidth=2,
            tabs=(self._font.measure("    "),),
            bg=self._background,
            fg=self._foreground,
            insertbackground="#f3f4f6",
            selectbackground="#1d4ed8",
            selectforeground="#eff6ff",
            yscrollcommand=self._on_text_scroll,
        )
        self.line_numbers.configure(
            font=self.text_widget.cget("font"),
            bg=self._gutter_background,
            fg=self._gutter_foreground,
            insertbackground=self._gutter_foreground,
            selectbackground=self._gutter_background,
            selectforeground=self._gutter_foreground,
        )

        self.percolator = None
        self.colorizer = None
        if Percolator is not None and ColorDelegator is not None:
            self.percolator = Percolator(self.text_widget)
            self.colorizer = ColorDelegator()
            self.percolator.insertfilter(self.colorizer)
        self._configure_tags()
        self._bind_editor_keys()
        self._install_context_menu()
        self._bind_line_number_updates()
        self._refresh_line_numbers()

    def _configure_tags(self) -> None:
        defaults = {
            "COMMENT": {"foreground": "#6a9955", "background": self._background},
            "KEYWORD": {"foreground": "#4aa8ff", "background": self._background},
            "BUILTIN": {"foreground": "#d7ba7d", "background": self._background},
            "STRING": {"foreground": "#ce9178", "background": self._background},
            "DEFINITION": {"foreground": "#ffd166", "background": self._background},
            "SYNC": {"background": self._background},
            "TODO": {"background": self._background},
            "ERROR": {"foreground": "#ffffff", "background": "#7f1d1d"},
            "hit": {"foreground": "#ffffff", "background": self._background},
        }
        for tag_name, options in defaults.items():
            self.text_widget.tag_configure(tag_name, **options)

    def _bind_editor_keys(self) -> None:
        self.text_widget.bind("<Return>", self._handle_return, add=True)
        self.text_widget.bind("<KP_Enter>", self._handle_return, add=True)
        self.text_widget.bind("<Tab>", self._handle_tab, add=True)
        self.text_widget.bind("<Shift-Tab>", self._handle_shift_tab, add=True)
        self.text_widget.bind("<ISO_Left_Tab>", self._handle_shift_tab, add=True)
        self.text_widget.bind("<BackSpace>", self._handle_backspace, add=True)

    def _bind_line_number_updates(self) -> None:
        events = (
            "<KeyRelease>",
            "<ButtonRelease-1>",
            "<MouseWheel>",
            "<Button-4>",
            "<Button-5>",
            "<Configure>",
        )
        for event_name in events:
            self.text_widget.bind(event_name, self._schedule_line_number_refresh, add=True)

    def _schedule_line_number_refresh(self, _event=None) -> None:
        self.after_idle(self._refresh_line_numbers)

    def _on_scrollbar(self, *args) -> None:
        self.text_widget.yview(*args)
        self.line_numbers.yview(*args)
        self._schedule_line_number_refresh()

    def _on_text_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)
        self._schedule_line_number_refresh()

    def _refresh_line_numbers(self) -> None:
        end_line = int(self.text_widget.index("end-1c").split(".")[0])
        content = "\n".join(str(line) for line in range(1, end_line + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", content)
        self.line_numbers.configure(state="disabled")
        self.line_numbers.yview_moveto(self.text_widget.yview()[0])

    def _install_context_menu(self) -> None:
        menu = tk.Menu(self.text_widget, tearoff=False)
        menu.add_command(label="Cut", command=lambda: self.text_widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: self.text_widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: self.text_widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self.text_widget.event_generate("<<SelectAll>>"))
        self.text_widget.bind("<Button-3>", lambda event: self._show_context_menu(event, menu), add=True)

    @staticmethod
    def _show_context_menu(event, menu: tk.Menu) -> str:
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        return "break"

    def _handle_return(self, event) -> str:
        if self.text_widget.tag_ranges("sel"):
            self.text_widget.delete("sel.first", "sel.last")

        line_start = self.text_widget.index("insert linestart")
        line_end = self.text_widget.index("insert lineend")
        line_text = self.text_widget.get(line_start, line_end)
        before_cursor = self.text_widget.get(line_start, "insert")
        current_indent = self._leading_whitespace(before_cursor)
        stripped = before_cursor.strip()

        next_indent = current_indent
        if stripped.endswith(":"):
            next_indent += "    "
        elif stripped.startswith(DEDENT_TOKENS) and current_indent:
            next_indent = current_indent[4:] if len(current_indent) >= 4 else ""

        self.text_widget.insert("insert", "\n" + next_indent)
        return "break"

    def _handle_tab(self, event) -> str:
        if self.text_widget.tag_ranges("sel"):
            start_line = int(self.text_widget.index("sel.first").split(".")[0])
            end_line = int(self.text_widget.index("sel.last").split(".")[0])
            if self.text_widget.index("sel.last").endswith(".0"):
                end_line -= 1

            for line_number in range(start_line, end_line + 1):
                self.text_widget.insert(f"{line_number}.0", "    ")
            return "break"

        self.text_widget.insert("insert", "    ")
        return "break"

    def _handle_shift_tab(self, event) -> str:
        if self.text_widget.tag_ranges("sel"):
            start_line = int(self.text_widget.index("sel.first").split(".")[0])
            end_line = int(self.text_widget.index("sel.last").split(".")[0])
            if self.text_widget.index("sel.last").endswith(".0"):
                end_line -= 1

            for line_number in range(start_line, end_line + 1):
                self._dedent_line(line_number)
            return "break"

        current_line = int(self.text_widget.index("insert").split(".")[0])
        self._dedent_line(current_line)
        return "break"

    def _handle_backspace(self, event) -> str | None:
        line_start = self.text_widget.index("insert linestart")
        before_cursor = self.text_widget.get(line_start, "insert")
        if before_cursor.endswith("    ") and before_cursor.strip() == "":
            self.text_widget.delete("insert-4c", "insert")
            return "break"
        return None

    def _dedent_line(self, line_number: int) -> None:
        line_start = f"{line_number}.0"
        line_text = self.text_widget.get(line_start, f"{line_number}.0 lineend")
        if line_text.startswith("    "):
            self.text_widget.delete(line_start, f"{line_number}.4")
        elif line_text.startswith("\t"):
            self.text_widget.delete(line_start, f"{line_number}.1")

    @staticmethod
    def _leading_whitespace(text: str) -> str:
        index = 0
        while index < len(text) and text[index] in {" ", "\t"}:
            index += 1
        return text[:index]

    def get(self, start: str = "1.0", end: str = "end") -> str:
        return self.text_widget.get(start, end)

    def get_selected_text(self) -> str:
        if not self.text_widget.tag_ranges("sel"):
            return ""
        return self.text_widget.get("sel.first", "sel.last")

    def delete(self, start: str, end: str) -> None:
        self.text_widget.delete(start, end)
        self._schedule_line_number_refresh()

    def insert(self, index: str, text: str) -> None:
        self.text_widget.insert(index, text)
        self._schedule_line_number_refresh()

    def replace_all_text(self, text: str) -> None:
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", text)
        self._schedule_line_number_refresh()

    def focus_editor(self) -> None:
        self.text_widget.focus_set()