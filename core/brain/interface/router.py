import ollama

class Router:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name

    def route(self, user_input: str):
        prompt = (
            f"Categorize intent as EXACTLY ONE word from this list: CHAT, COMMAND, MEMORY, QUERY, IMAGINE.\n"
            f"- Use MEMORY for recalling facts or past conversations.\n"
            f"- Use IMAGINE if the user asks to hypothesize, theorize, brainstorm, or invent a novel solution.\n"
            f"Output absolutely nothing else but the single word.\n"
            f"Input: {user_input}\nIntent:"
        )
        try:
            intent = ollama.generate(model=self.model, prompt=prompt)['response'].strip().upper()
            # Fallback cleanup just in case the LLM appends a period
            intent = ''.join(e for e in intent if e.isalnum()) 
        except:
            intent = "CHAT"
        
        self.bus.publish(f"intent_{intent}", user_input)
        return intent