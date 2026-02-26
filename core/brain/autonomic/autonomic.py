import threading
import time

class AutonomicNervousSystem:
    def __init__(self, bus, interval=60):
        self.bus = bus
        self.interval = interval
        self.running = False
        self._thread = None

    def _loop(self):
        while self.running:
            self.bus.publish("heartbeat", time.time())
            time.sleep(self.interval)

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False