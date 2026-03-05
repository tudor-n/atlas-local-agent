import subprocess
import os
import re
from colorama import Fore

class MotorCortex:
    def __init__(self):
        # ── THE SANDBOX LOCK ─────────────────────────────────────────────
        # Change this to wherever you created your dummy folder!
        self.sandbox_path = "D:\\atlas_sandbox" 
        
        # Ensure the sandbox exists
        if not os.path.exists(self.sandbox_path):
            os.makedirs(self.sandbox_path)
            print(Fore.YELLOW + f" [MOTOR] Warning: Sandbox didn't exist. Created at {self.sandbox_path}")
        # ─────────────────────────────────────────────────────────────────

    def _sanitize_command(self, raw_output: str) -> str:
        """Strips markdown formatting like ```bash ... ``` from the LLM output."""
        clean_cmd = raw_output.strip()
        
        # Remove markdown code blocks if present
        if clean_cmd.startswith("```"):
            # Find the end of the first line (e.g., ```bash)
            first_newline = clean_cmd.find('\n')
            if first_newline != -1:
                clean_cmd = clean_cmd[first_newline+1:]
            
            # Find the closing backticks
            last_backticks = clean_cmd.rfind("```")
            if last_backticks != -1:
                clean_cmd = clean_cmd[:last_backticks]
                
        return clean_cmd.strip()

    def execute_worker_command(self, raw_command: str) -> str:
        """Executes a command strictly within the sandbox environment."""
        clean_command = self._sanitize_command(raw_command)
        
        if not clean_command:
            return "[ERROR] Worker generated an empty command."

        print(Fore.CYAN + f" [MOTOR] Executing: {clean_command}")

        # ── SECURITY PROTOCOLS ───────────────────────────────────────────
        # Prevent obvious directory traversal escapes
        if "cd .." in clean_command or "cd \\" in clean_command or "cd /" in clean_command:
            print(Fore.RED + " [MOTOR] Security Intervention: Sandbox escape attempted.")
            return "[SYSTEM REJECTED] Command attempted to escape the restricted sandbox environment."
        
        # Prevent dangerous system commands
        dangerous_keywords = ["format", "diskpart", "reg", "del /f /s /q C:\\"]
        if any(dk in clean_command.lower() for dk in dangerous_keywords):
            print(Fore.RED + " [MOTOR] Security Intervention: Dangerous command blocked.")
            return "[SYSTEM REJECTED] Command contained prohibited system-level operations."
        # ─────────────────────────────────────────────────────────────────

        try:
            # Execute the command locked inside the sandbox_path
            result = subprocess.run(
                clean_command,
                shell=True,
                cwd=self.sandbox_path,  # <--- The absolute lock
                capture_output=True,
                text=True,
                timeout=15  # Prevents infinite loops
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"[SUCCESS]\n{output}" if output else "[SUCCESS] Command executed with no output."
            else:
                return f"[ERROR]\n{result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return "[ERROR] Command execution timed out after 15 seconds."
        except Exception as e:
            return f"[CRITICAL ERROR] Motor cortex failure: {str(e)}"