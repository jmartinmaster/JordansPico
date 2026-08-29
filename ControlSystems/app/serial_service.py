from __future__ import annotations

import ast
import struct
import time
from dataclasses import dataclass, field

import serial
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo


class SerialTransportError(RuntimeError):
    pass


@dataclass(slots=True)
class SerialPortInfo:
    device: str
    description: str
    manufacturer: str = ""
    product: str = ""
    hardware_id: str = ""
    detected_device: str = "Unknown serial device"
    probe_state: str = "listed"
    probe_summary: str = "OS enumeration only"
    response_preview: str = ""
    verified: bool = False

    @property
    def label(self) -> str:
        status = "verified" if self.verified else "listed"
        return f"{self.device} - {self.detected_device} [{status}]"

    @property
    def detail_line(self) -> str:
        details = [self.description]
        if self.manufacturer:
            details.append(self.manufacturer)
        if self.product and self.product != self.description:
            details.append(self.product)
        if self.response_preview:
            details.append(f"response={self.response_preview}")
        details.append(self.probe_summary)
        return " | ".join(part for part in details if part)


@dataclass(slots=True)
class BoardFileNode:
    name: str
    path: str
    is_dir: bool
    size_bytes: int | None = None
    children: list["BoardFileNode"] = field(default_factory=list)


class MicroPythonSerialService:
    def __init__(self) -> None:
        self._serial: serial.Serial | None = None
        self._connected_port: str = ""
        self._connected_baud_rate: int = 115200
        self._runtime_mode: str = "unknown"

    @property
    def connected_port(self) -> str:
        return self._connected_port

    @property
    def runtime_mode(self) -> str:
        return self._runtime_mode

    def list_ports(self) -> list[SerialPortInfo]:
        ports = []
        for port in list_ports.comports():
            ports.append(self._build_port_info(port))
        return ports

    def connect(self, port: str, baud_rate: int) -> None:
        self.disconnect()
        try:
            connection = serial.Serial()
            connection.port = port
            connection.baudrate = baud_rate
            connection.timeout = 0.2
            connection.write_timeout = 1
            connection.inter_byte_timeout = 1
            connection.dsrdtr = False
            connection.rtscts = False
            connection.exclusive = True
            connection.dtr = False
            connection.rts = False
            connection.open()
            try:
                connection.dtr = True
                connection.rts = False
            except serial.SerialException:
                pass
            self._serial = connection
            time.sleep(1.5)
            self._prepare_repl_channel(connection)
            self._runtime_mode = self._detect_runtime_mode(connection)
            self._connected_port = port
            self._connected_baud_rate = baud_rate
        except serial.SerialException as exc:
            raise SerialTransportError(f"Unable to connect to {port}: {exc}") from exc

    def disconnect(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None
                self._connected_port = ""
                self._connected_baud_rate = 115200
                self._runtime_mode = "unknown"

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def execute(self, code: str, timeout: float = 4.0) -> tuple[str, str]:
        serial_port = self._require_connection()
        return self._execute_raw_repl(serial_port, code, timeout)

    def execute_friendly_command(self, command: str, timeout: float = 4.0) -> tuple[str, str]:
        serial_port = self._require_connection()
        cleaned = command.rstrip("\r\n")
        if not cleaned:
            return "", ""

        self._drain_waiting_input(serial_port)
        serial_port.write((cleaned + "\r\n").encode("utf-8"))
        serial_port.flush()
        payload = self._read_friendly_response(serial_port, timeout)
        text = payload.decode("utf-8", errors="replace")
        stdout, stderr = self._split_friendly_output(text)
        return stdout, stderr

    def _execute_raw_repl(self, serial_port: serial.Serial, code: str, timeout: float) -> tuple[str, str]:
        self._enter_raw_repl(serial_port)
        try:
            self._submit_code(serial_port, code.encode("utf-8"), timeout)
            stdout = self._read_until(serial_port, b"\x04", timeout)[:-1]
            stderr = self._read_until(serial_port, b"\x04", timeout)[:-1]
            self._read_until(serial_port, b">", timeout)
            if stdout.startswith(b"OK"):
                stdout = stdout[2:]
            return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
        finally:
            self._exit_raw_repl(serial_port)

    def interrupt_current_program(self) -> tuple[str, str]:
        serial_port = self._require_connection()
        serial_port.write(b"\x03\x03")
        serial_port.flush()
        time.sleep(0.2)
        output = self._read_available_bytes(serial_port, duration=0.6)
        return self._decode_output(output), ""

    def write_file(self, remote_path: str, content: str, chunk_size: int = 512) -> None:
        chunks = [content[index:index + chunk_size] for index in range(0, len(content), chunk_size)] or [""]
        for index, chunk in enumerate(chunks):
            mode = "w" if index == 0 else "a"
            command = (
                f"with open({remote_path!r}, {mode!r}) as _handle:\n"
                f"    _handle.write({chunk!r})\n"
                f"print('chunk', {index + 1}, 'written')\n"
            )
            self.execute(command, timeout=max(4.0, len(chunk) / 100.0))

    def load_runtime_module(self, module_name: str) -> tuple[str, str]:
        command = (
            "import sys\n"
            f"sys.modules.pop({module_name!r}, None)\n"
            f"import {module_name} as runtime_module\n"
            "print('runtime-status')\n"
            "print(runtime_module.status())\n"
        )
        return self.execute(command, timeout=5.0)

    def set_parameters(self, module_name: str, parameters: dict[str, object]) -> tuple[str, str]:
        command = (
            f"import {module_name} as runtime_module\n"
            f"runtime_module.set_params({parameters!r})\n"
            "print('runtime-status')\n"
            "print(runtime_module.status())\n"
        )
        return self.execute(command, timeout=4.0)

    def run_test(self, module_name: str) -> tuple[str, str]:
        return self.execute(
            f"import {module_name} as runtime_module\nprint(runtime_module.run_test())\n",
            timeout=15.0,
        )

    def stop_test(self, module_name: str) -> tuple[str, str]:
        return self.execute(
            f"import {module_name} as runtime_module\nprint(runtime_module.stop_test())\n",
            timeout=4.0,
        )

    def read_status(self, module_name: str) -> tuple[str, str]:
        return self.execute(
            f"import {module_name} as runtime_module\nprint(runtime_module.status())\n",
            timeout=4.0,
        )

    def list_board_files(self, directory: str = "/") -> list[str]:
        command = (
            "import os\n"
            f"target = {directory!r}\n"
            "entries = []\n"
            "prefix = '' if target in ('', '/') else target.rstrip('/') + '/'\n"
            "for item in (os.ilistdir(target) if target not in ('', '/') else os.ilistdir()):\n"
            "    suffix = '/' if len(item) > 1 and (item[1] & 0x4000) else ''\n"
            "    entries.append(prefix + item[0] + suffix)\n"
            "entries.sort()\n"
            "print(entries)\n"
        )
        stdout, stderr = self.execute(command, timeout=5.0)
        if stderr.strip():
            raise SerialTransportError(stderr.strip())
        return self._parse_last_literal(stdout, list)

    def list_board_directory(self, directory: str = "") -> list[BoardFileNode]:
        normalized_directory = self._normalize_board_directory(directory)
        command = (
            "import os\n"
            f"target = {normalized_directory!r}\n"
            "print(list(os.ilistdir(target) if target else os.ilistdir()))\n"
        )
        stdout, stderr = self.execute(command, timeout=5.0)
        if stderr.strip():
            raise SerialTransportError(stderr.strip())
        entries = self._parse_last_literal(stdout, list)
        nodes = []
        for entry in entries:
            if not isinstance(entry, (tuple, list)) or not entry:
                continue
            name = str(entry[0])
            is_dir = False
            size_bytes: int | None = None
            if len(entry) >= 4 and isinstance(entry[1], int):
                mode = int(entry[1])
                is_dir = (mode & 0o170000) == 0o040000 or bool(mode & 0x4000)
                size_bytes = int(entry[3]) if not is_dir else None
            elif len(entry) >= 2:
                is_dir, size_bytes = self._parse_board_stat(entry[1])
            nodes.append(
                BoardFileNode(
                    name=name,
                    path=self._join_board_path(normalized_directory, name),
                    is_dir=is_dir,
                    size_bytes=size_bytes,
                )
            )
        nodes.sort(key=lambda item: (not item.is_dir, item.name.lower()))
        return nodes

    def read_board_file(self, remote_path: str, chunk_size: int = 256) -> str:
        command = (
            "_chunks = []\n"
            f"with open({remote_path!r}, 'rb') as _handle:\n"
            "    while True:\n"
            f"        _chunk = _handle.read({chunk_size})\n"
            "        if not _chunk:\n"
            "            break\n"
            "        _chunks.append(_chunk)\n"
            "print(_chunks)\n"
        )
        stdout, stderr = self.execute(command, timeout=8.0)
        if stderr.strip():
            raise SerialTransportError(stderr.strip())
        try:
            chunks = self._parse_last_literal(stdout, list)
            payload = bytearray()
            for chunk in chunks:
                if isinstance(chunk, bytes):
                    payload.extend(chunk)
                else:
                    payload.extend(str(chunk).encode("utf-8"))
            return payload.decode("utf-8")
        except (ValueError, SyntaxError, UnicodeDecodeError) as exc:
            raise SerialTransportError(f"Unable to parse board file contents for {remote_path}.") from exc

    def run_board_file(self, remote_path: str) -> tuple[str, str]:
        command = (
            f"__path = {remote_path!r}\n"
            "with open(__path, 'r') as _handle:\n"
            "    __source = _handle.read()\n"
            "exec(compile(__source, __path, 'exec'), globals(), globals())\n"
            "print('board-script-finished')\n"
        )
        return self.execute(command, timeout=15.0)

    def _require_connection(self) -> serial.Serial:
        if self._serial is None or not self._serial.is_open:
            raise SerialTransportError("Connect to the RP2040 board before running commands.")
        return self._serial

    def _enter_raw_repl(self, serial_port: serial.Serial) -> None:
        attempts: list[bytes] = []
        for _ in range(2):
            self._prepare_repl_channel(serial_port)
            self._drain_waiting_input(serial_port)

            serial_port.write(b"\r\x03\x03")
            serial_port.flush()
            time.sleep(0.1)
            attempts.append(self._drain_waiting_input(serial_port))

            serial_port.write(b"\x02")
            serial_port.flush()
            time.sleep(0.05)
            attempts.append(self._read_available_bytes(serial_port, duration=0.25, limit=256))

            serial_port.write(b"\r\n")
            serial_port.flush()
            time.sleep(0.1)
            attempts.append(self._read_available_bytes(serial_port, duration=0.4, limit=512))

            serial_port.write(b"\r\x01")
            serial_port.flush()
            data = self._read_available_bytes(serial_port, duration=1.5, limit=2048)
            normalized = data.replace(b"\r\r\n", b"\r\n")
            attempts.append(normalized)
            if b"raw REPL; CTRL-B to exit\r\n>" in normalized or normalized.rstrip().endswith(b">"):
                return

        preview = self._sanitize_preview(b" ".join(part for part in attempts if part))
        raise SerialTransportError(f"Unable to enter raw REPL. Received: {preview!r}")

    def _exit_raw_repl(self, serial_port: serial.Serial) -> None:
        serial_port.write(b"\r\x02")
        serial_port.flush()
        time.sleep(0.1)
        serial_port.reset_input_buffer()

    def _read_until(self, serial_port: serial.Serial, marker: bytes, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        while time.monotonic() < deadline:
            try:
                chunk = serial_port.read(1)
            except serial.SerialException as exc:
                raise SerialTransportError(f"Serial read failed while waiting for {marker!r}: {exc}") from exc
            if chunk:
                buffer.extend(chunk)
                if buffer.endswith(marker):
                    return bytes(buffer)
                continue
            time.sleep(0.01)
        raise SerialTransportError(f"Timed out waiting for {marker!r}. Received: {bytes(buffer)!r}")

    def _build_port_info(self, port: ListPortInfo) -> SerialPortInfo:
        detected_device = self._classify_device(port, "")

        if self.is_connected() and port.device == self._connected_port:
            return SerialPortInfo(
                device=port.device,
                description=port.description or "Unknown device",
                manufacturer=port.manufacturer or "",
                product=port.product or "",
                hardware_id=port.hwid or "",
                detected_device=detected_device,
                probe_state="connected",
                probe_summary="Already connected to control studio",
                verified=True,
            )

        probe_state, probe_summary, response_preview, verified = self._probe_port(port.device)
        detected_device = self._classify_device(port, response_preview)
        if not verified and self._looks_like_supported_board(port, detected_device):
            probe_state = "metadata-verified"
            probe_summary = "Verified from USB metadata despite silent probe"
            verified = True
        return SerialPortInfo(
            device=port.device,
            description=port.description or "Unknown device",
            manufacturer=port.manufacturer or "",
            product=port.product or "",
            hardware_id=port.hwid or "",
            detected_device=detected_device,
            probe_state=probe_state,
            probe_summary=probe_summary,
            response_preview=response_preview,
            verified=verified,
        )

    def _probe_port(self, device: str) -> tuple[str, str, str, bool]:
        try:
            probe = serial.Serial()
            probe.port = device
            probe.baudrate = 115200
            probe.timeout = 0.12
            probe.write_timeout = 0.12
            probe.inter_byte_timeout = 1
            probe.dsrdtr = False
            probe.rtscts = False
            probe.exclusive = True
            probe.dtr = False
            probe.rts = False

            with probe:
                try:
                    probe.dtr = True
                    probe.rts = False
                except serial.SerialException:
                    pass
                time.sleep(0.2)
                passive_bytes = self._read_available(probe, duration=0.18)
                if passive_bytes.strip():
                    return "passive-read", "Device responded without prompting", passive_bytes, True

                probe.write(b"\r\n")
                probe.flush()
                ping_bytes = self._read_available(probe, duration=0.22)
                if ping_bytes.strip():
                    return "newline-ping", "Device responded to newline ping", ping_bytes, True

                return "open-ok", "Port opened but did not answer probe", "", True
        except serial.SerialException as exc:
            return "open-failed", f"Unable to open port: {exc}", "", False
        except OSError as exc:
            return "probe-failed", f"Probe failed: {exc}", "", False

    def _read_available(self, serial_port: serial.Serial, duration: float, limit: int = 160) -> str:
        return self._sanitize_preview(self._read_available_bytes(serial_port, duration, limit))

    def _prepare_repl_channel(self, serial_port: serial.Serial) -> None:
        try:
            serial_port.reset_input_buffer()
        except Exception:
            pass
        try:
            serial_port.reset_output_buffer()
        except Exception:
            pass
        self._read_available_bytes(serial_port, duration=0.35)

    def _detect_runtime_mode(self, serial_port: serial.Serial) -> str:
        self._drain_waiting_input(serial_port)
        serial_port.write(b"\r\n")
        serial_port.flush()
        payload = self._read_available_bytes(serial_port, duration=0.5, limit=512)
        normalized = payload.replace(b"\r\r\n", b"\r\n")
        if b"Enter command:" in normalized:
            return "friendly-main"
        if b">>>" in normalized:
            return "friendly-python"
        if b"raw REPL; CTRL-B to exit" in normalized:
            return "raw-repl"
        return "unknown"

    def _drain_waiting_input(self, serial_port: serial.Serial) -> bytes:
        buffer = bytearray()
        waiting = getattr(serial_port, "in_waiting", 0)
        while waiting:
            try:
                buffer.extend(serial_port.read(waiting))
            except serial.SerialException:
                break
            waiting = getattr(serial_port, "in_waiting", 0)
        return bytes(buffer)


    def _submit_code(self, serial_port: serial.Serial, command_bytes: bytes, timeout: float) -> None:
        if self._try_raw_paste(serial_port, command_bytes, timeout):
            return

        for index in range(0, len(command_bytes), 64):
            serial_port.write(command_bytes[index:index + 64])
            serial_port.flush()
            time.sleep(0.01)

        serial_port.write(b"\x04")
        serial_port.flush()

    def _try_raw_paste(self, serial_port: serial.Serial, command_bytes: bytes, timeout: float) -> bool:
        serial_port.write(b"\x05A\x01")
        serial_port.flush()
        response = self._read_exact(serial_port, 2, 0.5)
        if response == b"R\x00":
            return False
        if response != b"R\x01":
            if response:
                self._read_available_bytes(serial_port, duration=0.1, limit=128)
            return False

        header = self._read_exact(serial_port, 2, 0.5)
        if len(header) != 2:
            raise SerialTransportError(f"Unable to read raw-paste header: {header!r}")

        window_size = struct.unpack("<H", header)[0]
        window_remaining = window_size
        index = 0
        while index < len(command_bytes):
            while window_remaining == 0 or serial_port.in_waiting:
                token = self._read_exact(serial_port, 1, timeout)
                if token == b"\x01":
                    window_remaining += window_size
                elif token == b"\x04":
                    serial_port.write(b"\x04")
                    serial_port.flush()
                    return True
                else:
                    raise SerialTransportError(f"Unexpected raw-paste token: {token!r}")

            chunk = command_bytes[index:index + window_remaining]
            serial_port.write(chunk)
            serial_port.flush()
            index += len(chunk)
            window_remaining -= len(chunk)

        serial_port.write(b"\x04")
        serial_port.flush()
        while True:
            end_token = self._read_exact(serial_port, 1, timeout)
            if end_token == b"\x01":
                continue
            if end_token == b"\x04":
                break
            raise SerialTransportError(f"Raw-paste did not terminate cleanly: {end_token!r}")
        return True

    def _read_exact(self, serial_port: serial.Serial, count: int, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        while len(buffer) < count and time.monotonic() < deadline:
            try:
                chunk = serial_port.read(count - len(buffer))
            except serial.SerialException as exc:
                raise SerialTransportError(f"Serial read failed while waiting for {count} bytes: {exc}") from exc
            if chunk:
                buffer.extend(chunk)
                continue
            time.sleep(0.01)
        return bytes(buffer)

    def _read_available_bytes(self, serial_port: serial.Serial, duration: float, limit: int = 512) -> bytes:
        deadline = time.monotonic() + duration
        buffer = bytearray()
        while time.monotonic() < deadline and len(buffer) < limit:
            waiting = serial_port.in_waiting
            if waiting:
                buffer.extend(serial_port.read(min(waiting, limit - len(buffer))))
                continue
            time.sleep(0.01)
        return bytes(buffer)

    def _sanitize_preview(self, payload: bytes) -> str:
        text = payload.decode("utf-8", errors="replace").replace("\r", " ").replace("\n", " ").strip()
        return " ".join(text.split())[:80]

    def _decode_output(self, payload: bytes) -> str:
        return payload.decode("utf-8", errors="replace")

    def _read_friendly_response(self, serial_port: serial.Serial, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        quiet_deadline = 0.0
        buffer = bytearray()
        while time.monotonic() < deadline:
            chunk = self._read_available_bytes(serial_port, duration=0.12, limit=2048)
            if chunk:
                buffer.extend(chunk)
                quiet_deadline = time.monotonic() + 0.25
                normalized = bytes(buffer).replace(b"\r\r\n", b"\r\n")
                if normalized.rstrip().endswith(b"Enter command:"):
                    break
                continue
            if quiet_deadline and time.monotonic() >= quiet_deadline:
                break
        return bytes(buffer)

    def _split_friendly_output(self, text: str) -> tuple[str, str]:
        cleaned = text.replace("\r\r\n", "\r\n")
        if "Traceback (most recent call last):" in cleaned:
            trace_start = cleaned.index("Traceback (most recent call last):")
            stdout = cleaned[:trace_start]
            stderr = cleaned[trace_start:]
        else:
            stdout = cleaned
            stderr = ""

        prompt = "Enter command:"
        if stdout.rstrip().endswith(prompt):
            stdout = stdout.rstrip()
            stdout = stdout[: -len(prompt)].rstrip()
        if stderr.rstrip().endswith(prompt):
            stderr = stderr.rstrip()
            stderr = stderr[: -len(prompt)].rstrip()
        return stdout, stderr

    def _parse_last_literal(self, output: str, expected_type: type):
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                value = ast.literal_eval(line)
            except (ValueError, SyntaxError):
                continue
            if isinstance(value, expected_type):
                return value
        raise SerialTransportError(f"Unable to parse response from board: {output!r}")

    def _normalize_board_directory(self, directory: str) -> str:
        cleaned = directory.strip()
        if cleaned in {"", "/"}:
            return ""
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned.lstrip("/")
        return cleaned.rstrip("/") or ""

    def _join_board_path(self, parent: str, name: str) -> str:
        normalized_parent = self._normalize_board_directory(parent)
        if not normalized_parent:
            return "/" + name
        return normalized_parent + "/" + name

    def _parse_board_stat(self, stat_value: object) -> tuple[bool, int | None]:
        if isinstance(stat_value, int):
            return False, stat_value
        if isinstance(stat_value, tuple) and stat_value:
            mode = int(stat_value[0])
            is_dir = (mode & 0o170000) == 0o040000 or bool(mode & 0x4000)
            size_bytes = None if is_dir else int(stat_value[6]) if len(stat_value) > 6 else None
            return is_dir, size_bytes
        return False, None

    def _classify_device(self, port: ListPortInfo, response_preview: str) -> str:
        source = " ".join(
            filter(
                None,
                [
                    port.description,
                    port.manufacturer,
                    port.product,
                    port.hwid,
                    response_preview,
                ],
            )
        ).lower()

        if "micropython" in source:
            return "MicroPython device"
        if "circuitpython" in source:
            return "CircuitPython device"
        if "raspberry pi pico" in source or "rp2040" in source or "pico" in source:
            return "RP2040 / Raspberry Pi Pico"
        if "arduino" in source:
            return "Arduino-compatible device"
        if "silicon labs" in source or "cp210" in source:
            return "USB UART bridge (CP210x)"
        if "wch" in source or "ch340" in source or "ch341" in source:
            return "USB UART bridge (CH34x)"
        if "ftdi" in source or "ft232" in source:
            return "USB UART bridge (FTDI)"
        if "cdc" in source:
            return "USB CDC serial device"
        if port.manufacturer or port.product:
            label = " ".join(part for part in [port.manufacturer, port.product] if part)
            return label or "USB serial device"
        return "Unknown serial device"

    def _looks_like_supported_board(self, port: ListPortInfo, detected_device: str) -> bool:
        source = " ".join(
            filter(
                None,
                [
                    detected_device,
                    port.description,
                    port.manufacturer,
                    port.product,
                    port.hwid,
                ],
            )
        ).lower()
        return any(token in source for token in ["rp2040", "raspberry pi pico", "micropython", "usb cdc"])