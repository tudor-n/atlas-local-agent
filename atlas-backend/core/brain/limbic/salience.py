import re
from colorama import Fore

_HIGH_SALIENCE = frozenset([
    "crash","crashed","emergency","urgent","critical","broken","failed","failure","error",
    "disaster","help","now","immediately","asap","fire","danger","lost","corrupted",
    "deleted","gone","dead","down","attack","breach","virus","malware","overflow","leak"
])
_NUMERIC_URGENCY = re.compile(r'\b(100|9[0-9])\s*%', re.IGNORECASE)

class SalienceFilter:
    def __init__(self, bus, model_name=None):
        self.bus = bus

    def score_importance(self, text: str) -> int:
        lower = text.lower()
        tokens = set(re.findall(r'\b\w+\b', lower))
        hits = len(_HIGH_SALIENCE & tokens)
        has_numeric = bool(_NUMERIC_URGENCY.search(lower))
        exclamations = text.count('!')
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

        score = 5
        score += min(hits * 2, 4)
        if has_numeric: score += 1
        score += min(exclamations, 2)
        if caps_ratio > 0.3: score += 1
        score = min(max(score, 1), 10)

        if score >= 9:
            self.bus.publish("high_salience_event", text)
        return score