import ollama

class Executive:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name

    def plan_execution(self, objective: str) -> list:
        prompt = f"Break this objective into 3 concrete, actionable steps. Return ONLY a comma-separated list.\nObjective: {objective}\nSteps:"
        try:
            response = ollama.generate(model=self.model, prompt=prompt)['response']
            steps = [s.strip() for s in response.split(',') if s.strip()]
            self.bus.publish("plan_created", steps)
            return steps
        except:
            return []