import string
import json
from pathlib import Path
from colorama import Fore

class HabitLoop:
    def __init__(self, bus, filepath="atlas_habits.json"):
        self.bus = bus
        self.filepath = Path(filepath)
        self.habits = self._load_habits()
        
        # Listen for neuro-plasticity updates from the Brain
        self.bus.subscribe("learn_new_habit", self._handle_new_habit)

    def _load_habits(self):
        if self.filepath.exists():
            try:
                return json.loads(self.filepath.read_text())
            except Exception:
                pass
        
        # Default fallback habits
        default_habits = {
            "hello atlas": "Good to see you, Sir.",
            "status report": "All core systems nominal, Sir."
        }
        self._save_habits(default_habits)
        return default_habits

    def _save_habits(self, habits_dict=None):
        if habits_dict is None: 
            habits_dict = self.habits
        self.filepath.write_text(json.dumps(habits_dict, indent=4))

    def _handle_new_habit(self, data):
        trigger = data.get("trigger", "")
        response = data.get("response", "")
        if trigger and response:
            normalized_trigger = trigger.lower().translate(str.maketrans('', '', string.punctuation)).strip()
            self.habits[normalized_trigger] = response
            self._save_habits()
            print(Fore.MAGENTA + f"\n [BASAL GANGLIA] New neuro-pathway formed: '{normalized_trigger}' -> '{response}'")

    def check_trigger(self, input_text: str) -> str:
        normalized = input_text.lower().translate(str.maketrans('', '', string.punctuation)).strip()
        if normalized in self.habits:
            self.bus.publish("habit_triggered", normalized)
            return self.habits[normalized]
        return ""