import json
from pathlib import Path

class RewardSystem:
    def __init__(self, path="atlas_rewards.json"):
        self.path = Path(path)
        self.weights = json.loads(self.path.read_text()) if self.path.exists() else {}

    def apply_feedback(self, action: str, positive: bool):
        current = self.weights.get(action, 1.0)
        self.weights[action] = min(max(current + (0.1 if positive else -0.1), 0.1), 2.0)
        self.path.write_text(json.dumps(self.weights))

    def get_weight(self, action: str) -> float:
        return self.weights.get(action, 1.0)