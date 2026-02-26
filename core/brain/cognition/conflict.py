class ConflictResolver:
    def __init__(self, bus):
        self.bus = bus
        self.threshold = 0.5

    def resolve(self, probabilities: dict) -> str:
        if not probabilities: return "fallback"
        top_intent = max(probabilities, key=probabilities.get)
        if probabilities[top_intent] < self.threshold:
            self.bus.publish("ambiguity_detected", probabilities)
            return "ask_clarification"
        return top_intent