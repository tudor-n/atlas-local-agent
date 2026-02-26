import psutil

class Interoception:
    def __init__(self, bus):
        self.bus = bus

    def get_vitals(self) -> dict:
        vitals = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        if vitals["cpu_percent"] > 90 or vitals["ram_percent"] > 90:
            self.bus.publish("high_resource_warning", vitals)
        return vitals