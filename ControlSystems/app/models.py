from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALUE_TYPES = ("int", "float", "bool", "str", "json")


def convert_parameter_value(raw_value: str, value_type: str) -> Any:
    text = raw_value.strip()

    if value_type == "int":
        return int(text or "0")
    if value_type == "float":
        return float(text or "0")
    if value_type == "bool":
        lowered = text.lower()
        return lowered in {"1", "true", "yes", "on"}
    if value_type == "json":
        return json.loads(text or "null")

    return text


def serialize_parameter_value(value: Any, value_type: str) -> str:
    if value_type == "json":
        return json.dumps(value)
    if value_type == "bool":
        return "true" if bool(value) else "false"
    return str(value)


@dataclass(slots=True)
class ParameterDefinition:
    name: str
    value_type: str
    raw_value: str

    def to_runtime_value(self) -> Any:
        return convert_parameter_value(self.raw_value, self.value_type)

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "value_type": self.value_type,
            "raw_value": self.raw_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParameterDefinition":
        value_type = str(data.get("value_type", "str"))
        if value_type not in VALUE_TYPES:
            value_type = "str"

        raw_value = data.get("raw_value")
        if raw_value is None and "value" in data:
            raw_value = serialize_parameter_value(data["value"], value_type)

        return cls(
            name=str(data.get("name", "parameter")).strip() or "parameter",
            value_type=value_type,
            raw_value=str(raw_value or ""),
        )


@dataclass(slots=True)
class ControlProject:
    project_name: str = "rp2040_starter"
    module_name: str = "control_runtime"
    port: str = ""
    baud_rate: int = 115200
    parameters: list[ParameterDefinition] = field(default_factory=list)
    script_text: str = ""

    def parameter_mapping(self) -> dict[str, Any]:
        return {item.name: item.to_runtime_value() for item in self.parameters if item.name.strip()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "module_name": self.module_name,
            "port": self.port,
            "baud_rate": self.baud_rate,
            "parameters": [item.to_dict() for item in self.parameters],
            "script_text": self.script_text,
        }

    def save(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "ControlProject":
        data = json.loads(source.read_text(encoding="utf-8"))
        project = cls(
            project_name=str(data.get("project_name", "rp2040_starter")),
            module_name=str(data.get("module_name", "control_runtime")),
            port=str(data.get("port", "")),
            baud_rate=int(data.get("baud_rate", 115200)),
            parameters=[ParameterDefinition.from_dict(item) for item in data.get("parameters", [])],
            script_text=str(data.get("script_text", "")),
        )
        return project


def default_parameters() -> list[ParameterDefinition]:
    return [
        ParameterDefinition("led_pin", "int", "25"),
        ParameterDefinition("led_on", "bool", "false"),
        ParameterDefinition("pwm_pin", "int", "15"),
        ParameterDefinition("frequency", "int", "1000"),
        ParameterDefinition("duty_cycle", "int", "32768"),
        ParameterDefinition("pwm_enabled", "bool", "true"),
        ParameterDefinition("test_cycles", "int", "12"),
        ParameterDefinition("pulse_ms", "int", "120"),
    ]


def python_literal(value: Any) -> str:
    return repr(value)


def coerce_text_to_python(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value