from __future__ import annotations

from textwrap import dedent, indent

from .models import ControlProject, python_literal


def default_board_logic() -> str:
    return dedent(
        """
        def apply_parameters():
            global _LED, _PWM, _CURRENT_LED_PIN, _CURRENT_PWM_PIN

            led_pin = int(PARAMETERS.get("led_pin", 25))
            if _LED is None or _CURRENT_LED_PIN != led_pin:
                _LED = Pin(led_pin, Pin.OUT)
                _CURRENT_LED_PIN = led_pin

            pwm_pin = PARAMETERS.get("pwm_pin")
            if pwm_pin is not None:
                pwm_pin = int(pwm_pin)
                if _PWM is None or _CURRENT_PWM_PIN != pwm_pin:
                    if _PWM is not None:
                        _PWM.deinit()
                    _PWM = PWM(Pin(pwm_pin))
                    _CURRENT_PWM_PIN = pwm_pin
                _PWM.freq(int(PARAMETERS.get("frequency", 1000)))
                if bool(PARAMETERS.get("pwm_enabled", True)):
                    duty_value = int(PARAMETERS.get("duty_cycle", 0))
                    duty_value = max(0, min(65535, duty_value))
                    _PWM.duty_u16(duty_value)
                else:
                    _PWM.duty_u16(0)

            _LED.value(1 if bool(PARAMETERS.get("led_on", False)) else 0)
            return status()


        def run_test():
            global _RUNNING

            apply_parameters()
            _RUNNING = True
            cycles = int(PARAMETERS.get("test_cycles", 10))
            pulse_ms = int(PARAMETERS.get("pulse_ms", 100))

            for _ in range(cycles):
                if not _RUNNING:
                    break

                _LED.value(0 if _LED.value() else 1)
                time.sleep_ms(pulse_ms)

            _RUNNING = False
            _LED.value(0)
            if _PWM is not None and not bool(PARAMETERS.get("pwm_enabled", True)):
                _PWM.duty_u16(0)
            return status()


        def stop_test():
            global _RUNNING

            _RUNNING = False
            if _LED is not None:
                _LED.value(0)
            if _PWM is not None:
                _PWM.duty_u16(0)
            return status()
        """
    ).strip()


def build_runtime_script(project: ControlProject) -> str:
    parameter_lines = []
    for parameter in project.parameters:
        if parameter.name.strip():
            parameter_lines.append(f"    {parameter.name!r}: {python_literal(parameter.to_runtime_value())},")

    parameter_block = "\n".join(parameter_lines) or "    'example_value': 0,"
    board_logic = project.script_text.strip() or default_board_logic()
    sections = [
        "from machine import Pin, PWM",
        "import time",
        "",
        "PARAMETERS = {",
        parameter_block,
        "}",
        "",
        "_RUNNING = False",
        "_LED = None",
        "_PWM = None",
        "_CURRENT_LED_PIN = None",
        "_CURRENT_PWM_PIN = None",
        "",
        "def set_param(name, value):",
        "    PARAMETERS[name] = value",
        "    return apply_parameters()",
        "",
        "def set_params(values):",
        "    for key, value in values.items():",
        "        PARAMETERS[key] = value",
        "    return apply_parameters()",
        "",
        "def status():",
        "    return {",
        '        "running": _RUNNING,',
        '        "parameters": PARAMETERS,',
        '        "led_pin": _CURRENT_LED_PIN,',
        '        "pwm_pin": _CURRENT_PWM_PIN,',
        "    }",
        "",
        board_logic,
        "",
        "apply_parameters()",
        'print("control-runtime-ready")',
        "print(status())",
    ]
    return "\n".join(sections).strip() + "\n"