import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from colorama import Fore

_QUEUE_PATH = Path("atlas_tasks.json")

class TaskQueue:
    def __init__(self, bus):
        self.bus = bus
        self._lock = threading.Lock()
        self.tasks = self._load()

    def _load(self) -> list:
        if _QUEUE_PATH.exists():
            try:
                return json.loads(_QUEUE_PATH.read_text())
            except:
                pass
        return []

    def _save(self):
        try:
            _QUEUE_PATH.write_text(json.dumps(self.tasks, indent=2))
        except Exception as e:
            print(Fore.RED + f" [TASK QUEUE] Save failed: {e}")

    def add(self, task: str, due_in_seconds: int = 0, priority: str = "normal") -> dict:
        with self._lock:
            entry = {
                "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "task": task,
                "due": (datetime.now() + timedelta(seconds=due_in_seconds)).isoformat(),
                "priority": priority,
                "status": "pending",
                "created": datetime.now().isoformat(),
            }
            self.tasks.append(entry)
            self._save()
            print(Fore.CYAN + f" [TASK QUEUE] Scheduled: '{task[:60]}' in {due_in_seconds}s")
            return entry

    def get_due(self) -> list:
        now = datetime.now()
        with self._lock:
            due = [t for t in self.tasks if t["status"] == "pending" and datetime.fromisoformat(t["due"]) <= now]
            for t in due:
                t["status"] = "fired"
            if due:
                self._save()
            return due

    def get_pending(self) -> list:
        with self._lock:
            return [t for t in self.tasks if t["status"] == "pending"]

    def complete(self, task_id: str):
        with self._lock:
            for t in self.tasks:
                if t["id"] == task_id:
                    t["status"] = "done"
            self._save()

    def cancel(self, task_id: str):
        with self._lock:
            for t in self.tasks:
                if t["id"] == task_id:
                    t["status"] = "cancelled"
            self._save()

    def list_pending_text(self) -> str:
        pending = self.get_pending()
        if not pending:
            return "No pending tasks, Sir."
        lines = []
        for t in sorted(pending, key=lambda x: x["due"]):
            due_dt = datetime.fromisoformat(t["due"])
            delta = due_dt - datetime.now()
            minutes = max(0, int(delta.total_seconds() // 60))
            lines.append(f"- [{t['priority'].upper()}] '{t['task'][:60]}' (due in {minutes}m)")
        return "\n".join(lines)