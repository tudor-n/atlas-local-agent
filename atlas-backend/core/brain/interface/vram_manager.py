"""
VRAM Manager — ensures only one Ollama model is loaded at a time.

RTX 5050 budget (8 GB total):
  ~1.5-2 GB  always resident  (Kokoro TTS + Faster-Whisper + sentence-transformers)
  ~5 GB      active model slot (butler OR worker — never both)

The 14b architect model is too large to coexist with anything;
it is routed to the cloud API (Gemini) by default.
"""

import threading
import ollama as _ollama
from colorama import Fore

# Keep-alive durations per role
_KEEP_ALIVE = {
    "butler":    "5m",   # conversational model — stays warm between exchanges
    "worker":    "2m",   # task model — short-lived
    "architect": 0,      # immediate unload (too large for 8 GB card)
}


class VRAMManager:
    """Singleton that serialises Ollama model loads so only one is hot."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._active_model = None
                    cls._instance._model_map = {}   # role -> model_name
        return cls._instance

    # ------------------------------------------------------------------
    def register(self, role: str, model_name: str):
        """Map a role (butler / worker / architect) to its Ollama model name."""
        self._model_map[role] = model_name

    # ------------------------------------------------------------------
    def ensure_loaded(self, role: str):
        """
        Make sure *role*'s model is the one currently in VRAM.
        If a different model is active, evict it first.
        """
        model = self._model_map.get(role)
        if not model:
            return

        if self._active_model == model:
            return                       # already hot — nothing to do

        # Evict the previous model
        if self._active_model:
            self._evict(self._active_model)

        # Warm the requested model with a single-token generate
        try:
            print(Fore.LIGHTBLACK_EX + f" [VRAM] Loading {role} ({model})...")
            _ollama.generate(
                model=model,
                prompt=".",
                keep_alive=_KEEP_ALIVE.get(role, "5m"),
                options={"num_predict": 1},
            )
            self._active_model = model
            print(Fore.LIGHTBLACK_EX + f" [VRAM] {role} ({model}) is now active.")
        except Exception as e:
            print(Fore.RED + f" [VRAM] Failed to load {role} ({model}): {e}")

    # ------------------------------------------------------------------
    def release(self, role: str):
        """Immediately evict a model (e.g. after an architect call)."""
        model = self._model_map.get(role)
        if model:
            self._evict(model)
            if self._active_model == model:
                self._active_model = None

    # ------------------------------------------------------------------
    def get_keep_alive(self, role: str):
        """Return the keep_alive value for a role."""
        return _KEEP_ALIVE.get(role, "5m")

    # ------------------------------------------------------------------
    def _evict(self, model: str):
        try:
            print(Fore.LIGHTBLACK_EX + f" [VRAM] Evicting {model}...")
            _ollama.generate(model=model, prompt=".", keep_alive=0, options={"num_predict": 1})
        except Exception:
            pass   # model may already be unloaded — that's fine


# Module-level convenience instance
vram = VRAMManager()
