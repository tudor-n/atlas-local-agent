class Critic:
    def __init__(self, bus):
        self.bus = bus
        self.banned_phrases = ["as an ai", "i cannot", "i apologize"]

    def evaluate(self, response: str) -> str:
        lower_resp = response.lower()
        if any(phrase in lower_resp for phrase in self.banned_phrases):
            self.bus.publish("critic_intervention", response)
            return "Sir, I encountered a processing constraint. Re-evaluating."
        return response