import threading
import time
from colorama import Fore

class AutonomicNervousSystem:
    def __init__(self, bus, interval=60):
        self.bus = bus
        self.interval = interval
        self.running = False
        self._thread = None
        self._task_queue = None

    def set_task_queue(self, tq):
        self._task_queue = tq

    def _loop(self):
        while self.running:
            self.bus.publish("heartbeat", time.time())
            if self._task_queue:
                due = self._task_queue.get_due()
                for task in due:
                    print(Fore.CYAN + f" [ANS] Task due: '{task['task'][:60]}'")
                    self.bus.publish("task_due", task)
            time.sleep(self.interval)

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False