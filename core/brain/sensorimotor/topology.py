class HabitLoop:
    def __init__(self, bus):
        self.bus = bus
        self.habits = {
            "hello atlas": "Good to see you, Sir.",
            "status report": "All core systems nominal, Sir."
        }

    def check_trigger(self, input_text: str) -> str:
        normalized = input_text.lower().strip()
        if normalized in self.habits:
            self.bus.publish("habit_triggered", normalized)
            return self.habits[normalized]
        return ""