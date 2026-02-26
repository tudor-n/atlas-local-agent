import ollama

class TheoryOfMind:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name
        self.user_state = {"mood": "neutral", "urgency": "low"}

    def analyze_state(self, user_input: str) -> dict:
        prompt = (
            "You are a strict data classification function. You cannot converse.\n"
            "Analyze the text and output EXACTLY one line in this format: Mood=[word], Urgency=[word]\n"
            "Options for Mood: positive, neutral, frustrated, panicked.\n"
            "Options for Urgency: low, high.\n\n"
            "Text: 'This is brilliant work!'\nOutput: Mood=positive, Urgency=low\n\n"
            "Text: 'My hard drive just crashed, help me!'\nOutput: Mood=panicked, Urgency=high\n\n"
            f"Text: '{user_input}'\nOutput:"
        )
        try:
            import ollama
            # Temperature forced to 0.0 for absolute mathematical determinism
            response = ollama.generate(model="llama3.1:latest", prompt=prompt, options={"temperature": 0.0})['response'].strip()
            
            mood = "neutral"
            urgency = "low"
            if "Mood=" in response:
                mood = response.split("Mood=")[1].split(",")[0].strip().lower()
            if "Urgency=" in response:
                urgency = response.split("Urgency=")[1].strip().lower()
                
            state = {"mood": mood, "urgency": urgency}
            self.bus.publish("user_state_updated", state)
            return state
        except:
            return {"mood": "neutral", "urgency": "low"}