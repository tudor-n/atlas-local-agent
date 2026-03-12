import ollama
import random

class DefaultModeNetwork:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name
        self.prompts = ["What is a novel way to optimize a local AI agent?", "What tech trend might affect my creator next?"]

    def daydream(self) -> str:
        prompt = random.choice(self.prompts)
        try:
            insight = ollama.generate(model=self.model, prompt=f"Briefly hypothesize: {prompt}")['response'].strip()
            self.bus.publish("insight_generated", insight)
            return insight
        except:
            return ""