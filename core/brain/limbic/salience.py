import ollama

class SalienceFilter:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name

    def score_importance(self, text: str) -> int:
        prompt = f"Rate the urgency/importance of this input from 1 to 10. Output ONLY the integer.\nInput: {text}\nScore:"
        try:
            score = int(ollama.generate(model=self.model, prompt=prompt)['response'].strip())
            if score >= 9: self.bus.publish("high_salience_event", text)
            return min(max(score, 1), 10)
        except:
            return 5