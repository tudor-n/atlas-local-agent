import subprocess

class MotorCortex:
    def __init__(self, bus):
        self.bus = bus

    def execute_command(self, command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout if result.returncode == 0 else result.stderr
            self.bus.publish("motor_executed", {"command": command, "success": result.returncode == 0})
            return output.strip()
        except subprocess.TimeoutExpired:
            return "Timeout"