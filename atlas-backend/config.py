import os

SANDBOX_PATH = "D:\\atlas_sandbox"
DOCKER_IMAGE = "python:3.10-slim"
CONTAINER_NAME = "atlas-worker-sandbox"
MEMORY_DB_PATH = "./atlas_memory"

WORKER_MODEL = "qwen2.5-coder:3b"
ARCHITECT_LOCAL_MODEL = "qwen2.5-coder:14b"
BUTLER_MODEL = "llama3.1:latest"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

WORKER_MAX_STEPS = 8
BASH_TIMEOUT = 15

# Legacy constant kept for any code that still references it.
# New code should use VRAMManager.get_keep_alive(role) instead.
OLLAMA_KEEP_ALIVE = "5m"

DMN_MIN_IDLE_SECONDS = 120
DMN_WANDER_INTERVAL_MIN = 120
DMN_WANDER_INTERVAL_MAX = 400

SESSION_SUMMARIZE_EVERY_N_TURNS = 16
SHORT_TERM_MEMORY_SIZE = 6
CONVERSATION_WINDOW = 6

VOICE_BLEND = {'bm_george': 0.7, 'bm_fable': 0.3}

ROUTER_COMMAND_ACTIONS = ["write", "make", "create", "build", "erase", "delete", "generate", "run", "execute", "compile", "install", "deploy", "open", "launch", "use"]
ROUTER_COMMAND_TARGETS = ["project", "c++", "cpp", "script", "file", "directory", "python", "code", "architect", "worker", "program", "app", "website", "server", "react", "node", "game"]
ROUTER_MEMORY_TRIGGERS = ["remember", "forget", "do you recall", "what do you know about me", "did i tell you", "what did we", "yesterday", "last time", "last session"]
ROUTER_QUERY_TRIGGERS = ["what is", "who is", "how does", "explain", "define", "what are", "tell me about", "how to", "why does", "when did", "where is"]

SALIENCE_URGENT_KEYWORDS = ["crash", "broken", "emergency", "urgent", "asap", "help me", "failing", "critical", "error", "not working", "down", "died", "destroyed"]
SALIENCE_HIGH_KEYWORDS = ["important", "deadline", "need", "must", "required", "priority", "fix", "issue", "problem", "bug"]

TOM_POSITIVE_KEYWORDS = ["thanks", "thank you", "great", "awesome", "perfect", "brilliant", "excellent", "nice", "good job", "well done", "love it", "amazing"]
TOM_FRUSTRATED_KEYWORDS = ["frustrated", "annoyed", "angry", "stupid", "broken", "useless", "terrible", "hate", "worst", "wrong", "ugh", "damn", "wtf", "fix this"]
TOM_PANICKED_KEYWORDS = ["help", "emergency", "crash", "lost everything", "oh no", "disaster", "panic"]