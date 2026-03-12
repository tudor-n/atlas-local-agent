import ollama
from colorama import Fore
from config import BUTLER_MODEL

class Executive:
    def __init__(self, bus, model_name=BUTLER_MODEL):
        self.bus = bus
        self.model = model_name

    def plan_execution(self, objective: str) -> list:
        prompt = (
            "You are a task planner for an AI agent. Break this objective into ordered, concrete steps.\n"
            "Rules: Maximum 5 steps. Each step must be a single, actionable instruction for a coding worker.\n"
            "Output ONLY a JSON array of strings. No explanation. No markdown.\n"
            "Example: [\"Read the existing main.py\", \"Add error handling to the parse function\", \"Save the updated file\"]\n"
            f"Objective: {objective}\nSteps:"
        )
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.0, "top_p": 0.1, "num_predict": 200}
            )['response'].strip()
            import json, re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                steps = json.loads(match.group(0))
                steps = [s.strip() for s in steps if isinstance(s, str) and s.strip()]
                if steps:
                    self.bus.publish("plan_created", steps)
                    return steps
        except Exception as e:
            print(Fore.RED + f" [EXECUTIVE] Planning failed: {e}")
        return [objective]