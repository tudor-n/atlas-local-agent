import subprocess
import os
import re
from colorama import Fore
from config import SANDBOX_PATH, BASH_TIMEOUT

class MotorCortex:
    def __init__(self, sandbox_path=SANDBOX_PATH):
        self.sandbox_path = sandbox_path
        os.makedirs(self.sandbox_path, exist_ok=True)

    def _sanitize_command(self, raw: str) -> str:
        clean = raw.strip()
        if clean.startswith("```"):
            nl = clean.find('\n')
            if nl != -1:
                clean = clean[nl + 1:]
            last = clean.rfind("```")
            if last != -1:
                clean = clean[:last]
        return clean.strip()

    def execute_worker_command(self, raw_command: str) -> str:
        clean = self._sanitize_command(raw_command)
        if not clean:
            return "[ERROR] Empty command."
        if re.search(r'\bcd\s*\.\.', clean) or re.search(r'\bcd\s*[/\\]', clean):
            return "[REJECTED] Sandbox escape blocked."
        dangerous = [r'\bdiskpart\b', r'\breg\s+(add|delete)\b', r'\bformat\s+[a-zA-Z]:', r'\bdel\s+/f\s+/s']
        for pat in dangerous:
            if re.search(pat, clean.lower()):
                return "[REJECTED] Dangerous command blocked."
        try:
            result = subprocess.run(clean, shell=True, cwd=self.sandbox_path, capture_output=True, text=True, timeout=BASH_TIMEOUT)
            if result.returncode == 0:
                out = result.stdout.strip()
                return f"[SUCCESS]\n{out}" if out else "[SUCCESS] No output."
            combined = f"{result.stderr.strip()}\n{result.stdout.strip()}".strip()
            return f"[ERROR]\n{combined}"
        except subprocess.TimeoutExpired:
            return f"[ERROR] Timed out after {BASH_TIMEOUT}s."
        except Exception as e:
            return f"[CRITICAL ERROR] {e}"