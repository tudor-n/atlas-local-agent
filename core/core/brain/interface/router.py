import ollama

class Router:
    def __init__(self, bus, model_name="llama3.1:latest"):
        self.bus = bus
        self.model = model_name
        # The ultimate whitelist. If the LLM hallucinates, we fall back safely.
        self.valid_intents = {"CHAT", "COMMAND", "MEMORY", "QUERY", "IMAGINE"}

    def route(self, user_input: str):

        input_lower = user_input.lower()
        
        # If the prompt contains BOTH an action word AND a technical target, force COMMAND instantly.
        action_words = ["write", "make", "create", "build", "erase", "delete", "use", "generate"]
        target_words = ["project", "c++", "cpp", "script", "file", "directory", "python", "code", "architect", "worker"]
        
        has_action = any(act in input_lower for act in action_words)
        has_target = any(tgt in input_lower for tgt in target_words)
        
        if has_action and has_target:
            from colorama import Fore
            print(Fore.MAGENTA + " [ROUTER] Heuristic override triggered: Forced COMMAND")
            self.bus.publish("intent_COMMAND", user_input)
            return "COMMAND"
        
        prompt = (
            "Categorize the user's input into EXACTLY ONE word from this list: CHAT, COMMAND, MEMORY, QUERY, IMAGINE.\n\n"
            "DEFINITIONS:\n"
            "- COMMAND: Interacting with the PC, writing code, creating multi-file projects, or invoking internal tools (like 'worker', 'architect'). ANY request mentioning a programming language (C++, Python, etc.) MUST be a COMMAND.\n"
            "- MEMORY: Recalling, saving, or forgetting personal facts or past conversations. DO NOT use this for PC files.\n"
            "- QUERY: General knowledge questions (e.g., 'What is the capital of France?').\n"
            "- IMAGINE: Hypothesizing, brainstorming, or creative writing (non-code).\n"
            "- CHAT: Casual conversation, greetings, or asking for non-code text (like essays or poems).\n\n"
            "EXAMPLES:\n"
            "Input: 'Write me a complete OOP chess project in C++'\nIntent: COMMAND\n"
            "Input: 'Use the worker node and the architect to do this'\nIntent: COMMAND\n"
            "Input: 'Write me a story about a dragon'\nIntent: CHAT\n"
            "Input: 'Erase the python file'\nIntent: COMMAND\n"
            "Input: 'Build a react website'\nIntent: COMMAND\n"
            f"Input: '{user_input}'\n"
            "Intent:"
        )
        
        try:
            # Generate and aggressively strip whitespace and newlines
            response = ollama.generate(model=self.model, prompt=prompt)['response'].strip().upper()
            
            # Strip out any random punctuation the LLM might add (like "COMMAND.")
            intent = ''.join(e for e in response if e.isalnum())
            
            # FAILSAFE: If the LLM hallucinates a word not in our list, default to CHAT
            if intent not in self.valid_intents:
                intent = "CHAT"
                
        except Exception as e:
            print(f"\n[ROUTER ERROR] Failed to parse intent: {e}")
            intent = "CHAT"
        
        self.bus.publish(f"intent_{intent}", user_input)
        return intent