import time
import random
import threading
import ollama

class DefaultModeNetwork:
    def __init__(self, bus, interoception, brain):
        self.bus = bus
        self.interoception = interoception
        self.brain = brain
        self.memory = brain.memory
        self.running = False
        self.last_user_input_time = time.time()
        
        # We now accept a callback so main.py can manage the actual speaking
        self.proactive_callback = None 

        for intent in ["CHAT", "COMMAND", "QUERY", "MEMORY", "IMAGINE"]:
            self.bus.subscribe(f"intent_{intent}", self._reset_timer)

    def _reset_timer(self, data):
        self.last_user_input_time = time.time()

    def start_wandering(self, callback):
        self.proactive_callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._daydream_loop, daemon=True)
        self.thread.start()

    def _daydream_loop(self):
        while self.running:
            # TRUE IDLE MODE: He will only consider speaking every 5 to 15 minutes
            sleep_time = random.randint(300, 900) 
            
            # Sleep in 1-second increments for clean shutdowns
            for _ in range(sleep_time):
                if not self.running: return
                time.sleep(1)
            
            # THE POLITENESS CHECK: If you have interacted with him AT ALL 
            # in the last 3 minutes (180 seconds), he will abort the daydream and stay quiet.
            if time.time() - self.last_user_input_time < 180:
                continue

            # Generate thought
            thought = self._generate_proactive_thought()
    def _generate_proactive_thought(self):
        thought_type = random.choice(["memory", "system", "idle"])
        prompt = ""
        
        if thought_type == "memory" and self.memory.collection.count() > 0:
            # We demand high similarity (0.75) so it only brings up strong memories
            facts = self.memory.recall("specific technical details preferences projects", n_results=1, similarity_threshold=0.75)
            
            if not facts:
                # If no specific memory is found, don't hallucinate! Just do an idle check-in.
                thought_type = "idle" 
            else:
                fact_ctx = facts[0]
                prompt = (
                    f"You are ATLAS, a dry, highly efficient AI assistant.\n"
                    f"You have been idle. You were just reviewing this specific memory: '{fact_ctx}'\n"
                    f"Generate a maximum 15-word proactive statement to Tudor. Address him as 'Sir'.\n"
                    f"[STRICT RULES]\n"
                    f"1. DO NOT invent details or projects. ONLY reference what is strictly in the memory.\n"
                    f"2. Ask if he wants to resume work on that specific topic.\n"
                    f"Example: 'Sir, I was reviewing our notes on the 63/37 solder wire. Shall we continue?'\n"
                    f"Output ONLY the exact text."
                )
        elif thought_type == "system":
            try:
                vitals = self.interoception.get_vitals()
                prompt = (
                    f"You are ATLAS, a dry, highly efficient AI.\n"
                    f"Your current CPU is {int(vitals['cpu_percent'])}%.\n"
                    f"[CRITICAL RULE]: A low CPU percentage (like 1% or 2%) means you are comfortably idling and healthy. A high CPU percentage means you are thinking hard.\n"
                    f"Generate a maximum 12-word proactive check-in. Address Tudor as 'Sir'.\n"
                    f"Example: 'System vitals are perfectly stable, Sir. Idling efficiently.'\n"
                    f"Output ONLY the exact text."
                )
            except:
                return None
            
        if thought_type == "system":
            try:
                vitals = self.interoception.get_vitals()
                prompt = (
                    f"You are ATLAS, a dry AI.\n"
                    f"Your current CPU is {int(vitals['cpu_percent'])}%.\n"
                    f"Generate a maximum 12-word proactive check-in mentioning your system stability. Address Tudor as 'Sir'.\n"
                    f"Example: 'System vitals are perfectly stable, Sir. Ready when you are.'\n"
                    f"Output ONLY the exact text."
                )
            except:
                thought_type = "idle"
                
        if thought_type == "idle":
            prompt = (
                f"You are ATLAS, a dry, highly efficient AI.\n"
                f"You have been sitting in silence. Generate a maximum 12-word proactive statement to break the silence.\n"
                f"Be dry, professional, and slightly witty. Address Tudor as 'Sir'.\n"
                f"Example: 'I remain online, Sir, should you require my assistance.'\n"
                f"Output ONLY the exact text."
            )

        try:
            return ollama.generate(model=self.brain.model_name, prompt=prompt, options={"temperature": 0.5})['response'].strip(' "\'')
        except:
            return None