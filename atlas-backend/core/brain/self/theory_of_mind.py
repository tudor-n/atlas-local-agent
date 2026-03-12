import re
from colorama import Fore

_POSITIVE = frozenset(["great","perfect","brilliant","excellent","thanks","thank","appreciate","love","awesome","amazing","nice","good","well done","superb","fantastic"])
_FRUSTRATED = frozenset(["wrong","broken","bad","hate","terrible","awful","stupid","useless","not working","doesn't work","failed","again","seriously","come on","ridiculous","frustrating","annoying"])
_PANICKED = frozenset(["crash","emergency","help","lost","corrupted","deleted","disaster","urgent","critical","gone","dead","destroyed","fire","please","asap","now"])
_HIGH_URGENCY = frozenset(["asap","immediately","urgent","critical","now","emergency","help","please","fast","quickly"])

class TheoryOfMind:
    def __init__(self, bus, model_name=None):
        self.bus = bus
        self.user_state = {"mood": "neutral", "urgency": "low"}

    def analyze_state(self, user_input: str) -> dict:
        lower = user_input.lower()
        tokens = set(re.findall(r'\b\w+\b', lower))
        bigrams = set()
        words = lower.split()
        for i in range(len(words)-1):
            bigrams.add(f"{words[i]} {words[i+1]}")
        all_tokens = tokens | bigrams

        panic_hits = len(_PANICKED & all_tokens)
        frustrated_hits = len(_FRUSTRATED & all_tokens)
        positive_hits = len(_POSITIVE & all_tokens)
        urgency_hits = len(_HIGH_URGENCY & all_tokens)
        exclamations = user_input.count('!')

        if panic_hits >= 2 or (panic_hits >= 1 and exclamations >= 1):
            mood = "panicked"
        elif frustrated_hits > positive_hits:
            mood = "frustrated"
        elif positive_hits > frustrated_hits:
            mood = "positive"
        else:
            mood = "neutral"

        urgency = "high" if (urgency_hits >= 1 or exclamations >= 2 or panic_hits >= 1) else "low"

        state = {"mood": mood, "urgency": urgency}
        self.user_state = state
        self.bus.publish("user_state_updated", state)
        return state