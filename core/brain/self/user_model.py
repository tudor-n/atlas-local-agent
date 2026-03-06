import json
import re
from pathlib import Path
from datetime import datetime
from colorama import Fore

_PROFILE_PATH = Path("atlas_user_model.json")

_DEFAULTS = {
    "technical_level": "expert",
    "prefers_concise": True,
    "active_projects": [],
    "frustration_triggers": [],
    "preferred_tools": [],
    "known_preferences": {},
    "interaction_count": 0,
    "last_seen": None,
    "frustration_streak": 0,
    "positive_streak": 0,
}

class UserModel:
    def __init__(self):
        self.profile = self._load()

    def _load(self) -> dict:
        if _PROFILE_PATH.exists():
            try:
                data = json.loads(_PROFILE_PATH.read_text())
                merged = dict(_DEFAULTS)
                merged.update(data)
                return merged
            except:
                pass
        return dict(_DEFAULTS)

    def _save(self):
        try:
            _PROFILE_PATH.write_text(json.dumps(self.profile, indent=2))
        except Exception as e:
            print(Fore.RED + f" [USER MODEL] Save failed: {e}")

    def update_from_interaction(self, user_input: str, mood: str, intent: str):
        self.profile["interaction_count"] += 1
        self.profile["last_seen"] = datetime.now().isoformat()

        if mood == "frustrated":
            self.profile["frustration_streak"] += 1
            self.profile["positive_streak"] = 0
            trigger = user_input[:80]
            if trigger not in self.profile["frustration_triggers"]:
                self.profile["frustration_triggers"].append(trigger)
                if len(self.profile["frustration_triggers"]) > 20:
                    self.profile["frustration_triggers"] = self.profile["frustration_triggers"][-20:]
        elif mood == "positive":
            self.profile["positive_streak"] += 1
            self.profile["frustration_streak"] = 0
        else:
            self.profile["frustration_streak"] = max(0, self.profile["frustration_streak"] - 1)

        lower = user_input.lower()
        project_match = re.search(r'(?:working on|project called|my project|building)\s+["\']?([a-zA-Z0-9_\- ]{3,30})["\']?', lower)
        if project_match:
            proj = project_match.group(1).strip().title()
            if proj not in self.profile["active_projects"]:
                self.profile["active_projects"].append(proj)
                if len(self.profile["active_projects"]) > 10:
                    self.profile["active_projects"] = self.profile["active_projects"][-10:]

        if "prefer" in lower or "i like" in lower or "i always" in lower:
            pref_match = re.search(r'(?:prefer|like|always use)\s+([a-zA-Z0-9_\- ]{3,40})', lower)
            if pref_match:
                pref = pref_match.group(1).strip()
                self.profile["known_preferences"][pref] = datetime.now().isoformat()

        self._save()

    def get_context_string(self) -> str:
        parts = []
        if self.profile["active_projects"]:
            parts.append(f"Active projects: {', '.join(self.profile['active_projects'][-3:])}")
        if self.profile["known_preferences"]:
            prefs = list(self.profile["known_preferences"].keys())[-5:]
            parts.append(f"Known preferences: {', '.join(prefs)}")
        if self.profile["frustration_streak"] >= 2:
            parts.append("Note: User has shown repeated frustration recently. Be more concise and direct.")
        return "\n".join(parts) if parts else ""

    def get(self, key, default=None):
        return self.profile.get(key, default)