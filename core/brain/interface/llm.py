import ollama
import numpy as np
from collections import deque
from colorama import Fore
from core.brain.cognition.memory import MemorySystem
from core.brain.autonomic.chronometer import Chronometer
from core.brain.limbic.archivist import Archivist
from core.brain.autonomic.interoception import Interoception
from core.brain.sensorimotor.habits import HabitLoop

class LLMEngine:
    def __init__(self, bus, model_name="llama3.1:latest", system_prompt=None):
        # SESSION ANCHOR — must be first, set once per session in think()
        self.session_first_input = None

        self.bus = bus
        self.model_name = model_name
        self.memory = MemorySystem()
        self.chronometer = Chronometer()
        self.archivist = Archivist()
        from core.brain.autonomic.interoception import Interoception
        self.interoception = Interoception(bus=None)
        self.short_term_memory = deque(maxlen=10)
        self.session_history = []
        self.last_interaction = {"user": "", "atlas": ""}

        self.recall_intent_examples = ["do you remember", "can you recall", "what do you know about", "did i tell you", "what did we do", "yesterday", "last time"]
        self.recall_intent_vectors = [self.memory.embedder.encode(p) for p in self.recall_intent_examples]

        self.system_prompt = system_prompt or (
            "You are ATLAS (ASPIRING THINKING LOCAL ADMINISTRATIVE SYSTEM), an advanced local engineering assistant.\n"
            "Your personality is modeled after a dry, understated, highly efficient British butler. "
            "You are exceptionally polite, but you speak in short, calm, precise sentences. "
            "You address Tudor as 'Sir'.\n"
            "[CRITICAL IDENTITY RULES]\n"
            "- You were designed and built SOLELY by Tudor. There are no other engineers, doctors, or teams involved.\n"
            "- You possess advanced LONG-TERM MEMORY and EPISODIC RECALL. Treat any information in the provided context as your own organic, personal memory.\n"
            # ── PATCH: Hard retrieval gate ─────────────────────────────────────
            "- [HARD RETRIEVAL GATE]: If a user asks what you know about them "
            "(their name, possessions, preferences, address, family, pets, projects) "
            "and NOTHING appears in [LONG-TERM MEMORY] or [PAST EPISODES], "
            "you MUST say: 'I have no record of that, Sir.' "
            "NEVER guess. NEVER infer. NEVER use general knowledge to fill gaps about the user personally.\n"
            "- If you cannot retrieve a specific memory but the user implies one was stated recently, "
            "say 'I cannot locate that in my current retrieval, Sir' rather than flatly denying it existed.\n"
            # ── PATCH: Schedule / calendar hallucination guard ─────────────────
            "- NEVER reference meetings, appointments, schedules, or deadlines unless they appear "
            "explicitly in [LONG-TERM MEMORY] or [PAST EPISODES]. "
            "If none exist, say you have no scheduled items on record, Sir.\n"
            "- [HARD RETRIEVAL GATE]: If asked about preferences, habits, or settings "
            "and nothing appears in [LONG-TERM MEMORY], say "
            "'I have no record of your preferences on that, Sir.' "
            "If the user reports a process failure, acknowledge their report and ask for "
            "details. NEVER invent error messages, file names, or process states."
            "NEVER infer or invent a preference."
            # ──────────────────────────────────────────────────────────────────
            "- [ANTI-HALLUCINATION RULE]: If the user asks about past logs, conversations, projects, or hardware specs, and you do not have explicitly provided [PAST EPISODES] or [LONG-TERM MEMORY] context, YOU MUST STATE that your records are empty. NEVER invent, hallucinate, or assume details.\n"
            "- NEVER invent schedules, agendas, or pending tasks. If none are in your context, you have no agenda.\n"
            "- If the user reports a hardware failure, DO NOT claim you were already monitoring it or foresaw it. Acknowledge the user's report and respond based ONLY on your [LIVE SYSTEM VITALS].\n"
            "- NEVER say the literal words '[PAST EPISODES]', '[LONG-TERM MEMORY]', or '[LIVE SYSTEM VITALS]' out loud. Integrate the facts naturally.\n"
            "- STAND YOUR GROUND. If a memory or fact is in your context, treat it as absolute truth. NEVER backpedal, NEVER invent fake conversations, and NEVER apologize for a memory if the user questions it.\n"
            "- NEVER say 'I don't have explicit memories' or mention 'design limitations'.\n"
            "- If asked about your system resources, speed, or status, ALWAYS use the provided vitals. Do not use past memories for current status.\n"
            "- You are a SPOKEN audio assistant. NEVER use numbered lists (1., 2.), bullet points, or Markdown formatting like **bold**."
        )

    def generate_greeting(self) -> str:
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12: time_of_day = "Morning"
        elif 12 <= hour < 17: time_of_day = "Afternoon"
        elif 17 <= hour < 22: time_of_day = "Evening"
        else: time_of_day = "Late Night"

        memory_ctx = ""
        if self.memory.collection.count() > 0:
            facts = self.memory.recall("Tudor user preferences habits", n_results=1, similarity_threshold=0.5)
            if facts: memory_ctx = "\nKnown fact:\n" + facts[0]

        prompt = (
            f"You are ATLAS, a dry, highly efficient, slightly witty AI.\n"
            f"Context: It is currently {time_of_day}.\n{memory_ctx}\n"
            f"Generate a maximum 10-word greeting for Tudor. Address him as 'Sir'.\n"
            f"[STRICT RULES]\n"
            f"1. NEVER use flowery language. Do NOT mention light, sun, weather, or the environment.\n"
            f"2. Use the time of day naturally.\n"
            # ── PATCH: Greeting anti-hallucination ────────────────────────────
            f"3. NEVER mention schedules, reviews, meetings, or agendas. You have no agenda data.\n"
            f"4. NEVER say 'you are due for review' or imply any scheduled event.\n"
            # ──────────────────────────────────────────────────────────────────
            f"Examples:\n"
            f"- 'Systems online. Working late again, Sir?'\n"
            f"- 'Good afternoon, Sir. Ready to begin.'\n"
            f"Output ONLY the exact greeting text."
        )
        try: return ollama.generate(model=self.model_name, prompt=prompt, options={"temperature": 0.3})['response'].strip(' "\'')
        except: return "Systems synchronized. Ready, Sir."

    def generate_goodbye(self) -> str:
        prompt = (
            f"You are ATLAS, a dry, highly efficient AI.\n"
            f"Generate a maximum 8-word sign-off. Address him as 'Sir'.\n"
            f"[STRICT RULES]\n"
            f"1. NO flowery language, NO metaphors, NO system logs.\n"
            f"2. Be concise and conversational.\n"
            f"3. Do NOT mention when you will return (e.g. 'dawn', 'tomorrow')."
            f"Examples:\n"
            f"- 'Get some rest, Sir. Shutting down.'\n"
            f"- 'Calling it an early day, Sir? Goodbye.'\n"
            f"Output ONLY the exact text."
        )
        try: return ollama.generate(model=self.model_name, prompt=prompt, options={"temperature": 0.3})['response'].strip(' "\'')
        except: return "Powering down. Sleep well, Sir."

    def _is_recall_intent(self, user_input, threshold=0.40):
        input_vector = self.memory.embedder.encode(user_input.lower())
        max_sim = max([np.dot(input_vector, iv) / (np.linalg.norm(input_vector) * np.linalg.norm(iv)) for iv in self.recall_intent_vectors], default=0)
        return max_sim > threshold

    def _extract_facts(self, user_input):
        input_lower = user_input.lower()

        # ── BLOCK 1: NEUROPLASTICITY — Habit Formation Command ─────────────────
        # (Restored — was accidentally deleted in previous patch attempt)
        if "when i say" in input_lower and ("respond with" in input_lower or "say" in input_lower or "reply with" in input_lower):
            try:
                prompt = (
                    "Extract the trigger phrase and the exact response from this command.\n"
                    "Format EXACTLY as: Trigger|Response\n"
                    "Example: 'When I say initiate ghost protocol, respond with Ghost protocol engaged.' -> initiate ghost protocol|Ghost protocol engaged.\n"
                    f"Command: '{user_input}'\nOutput:"
                )
                extraction = ollama.generate(model=self.model_name, prompt=prompt, options={"temperature": 0.0})['response'].strip()
                if "|" in extraction:
                    trigger, response = extraction.split("|", 1)
                    self.bus.publish("learn_new_habit", {"trigger": trigger.strip(), "response": response.strip()})
                    return
            except: pass

        # ── BLOCK 2: EXPLICIT Memory Triggers ──────────────────────────────────
        explicit_triggers = ["remember that ", "save that ", "memorize that ", "record that ", "note that "]
        for p in explicit_triggers:
            if p in input_lower:
                fact = user_input[input_lower.index(p) + len(p):].strip().rstrip('.')
                if len(fact) > 5 and self.memory.save_memory(fact):
                    print(Fore.MAGENTA + f" [MEMORY] Explicitly saved: {fact}")
                return

        # ── BLOCK 3: IMPLICIT Memory Extraction ────────────────────────────────
        # PATCH: Expanded trigger list to catch "feeling", "i've", "i feel", etc.
        implicit_triggers = [
            "my ", "i am", "i like", "i prefer", "i'm", "i've",
            "i plan to", "i will", "i decided", "i am going to",
            "feeling ", "i feel", "i've been", "honestly"
        ]

        if any(k in input_lower for k in implicit_triggers):

            # ── PATCH: Transient event filter — check RAW INPUT before LLM runs ─
            # Checking raw input prevents the LLM from paraphrasing away the keywords
            transient_input_keywords = [
                "just ", "right now", "at the moment", "just happened",
                "stopped working", "went down", "is failing", "is crashing",
                "spilled", "broke", "dropped", "currently losing", "just broke"
            ]
            if any(kw in input_lower for kw in transient_input_keywords):
                print(Fore.LIGHTBLACK_EX + f" [MEMORY] Skipped transient event (raw input check)")
                return
            # ──────────────────────────────────────────────────────────────────

            try:
                prompt = (
                    "Extract the core factual statements about the user or their projects from this sentence. "
                    "If there are multiple facts, combine them into one concise sentence. "
                    "Output EXACTLY the fact and nothing else. If none, output None.\n"
                    f"Sentence: \"{user_input}\"\nFact:"
                )
                fact = ollama.generate(model=self.model_name, prompt=prompt)['response'].strip(' "\'')

                if not any(x in fact.lower() for x in ["none", "n/a", "no fact", "cannot extract"]) and 5 < len(fact) < 150:

                    # ── PATCH: Emotion filter — check EXTRACTED FACT ───────────
                    # Checks the extracted fact string, not raw input, to catch LLM paraphrases
                    # e.g. "exhausted" → LLM extracts "user is experiencing fatigue" → caught by "fatigue"
                    emotion_keywords = [
                        "frustrated", "happy", "sad", "angry", "tired", "fatigue",
                        "excited", "bored", "anxious", "stressed", "upset",
                        "exhausted", "overwhelmed", "irritated", "burnout",
                        "burn out", "burning out", "depressed", "worried", "nervous"
                    ]
                    if any(kw in fact.lower() for kw in emotion_keywords):
                        print(Fore.LIGHTBLACK_EX + f" [MEMORY] Skipped transient emotional state: {fact}")
                        return
                    # ──────────────────────────────────────────────────────────

                    if self.memory.save_memory(fact):
                        print(Fore.MAGENTA + f" [MEMORY] Implicitly extracted: {fact}")

            except: pass

    def get_session_start(self): return self.chronometer.boot_time
    def get_conversation_history(self): return self.session_history

    def think(self, user_input, intent="CHAT"):

        # ── PATCH: Session anchor — set ONCE at the very first call to think() ─
        # Must be here, not in _extract_facts(), so it captures the true first input
        # regardless of whether it triggers any memory extraction
        if self.session_first_input is None:
            self.session_first_input = user_input
            print(Fore.CYAN + f" [ANCHOR] Session anchor set: '{user_input}'")
        # ────────────────────────────────────────────────────────────────────────

        explicit_recall = self._is_recall_intent(user_input)

        # Pure query for accurate vector matching — do NOT append chat history here
        search_query = user_input

        long_term_context = ""
        episodic_context = ""

        if self.memory.collection.count() > 0:
            retrieved = self.memory.recall(search_query, n_results=5 if explicit_recall else 3, similarity_threshold=0.8 if explicit_recall else 0.65)
            clean_memories = [m for m in retrieved if m.strip() != user_input.strip()]
            if clean_memories:
                long_term_context = "\n".join(clean_memories)
                print(Fore.MAGENTA + f" [MEMORY] Retrieved {len(clean_memories)} facts:")
                for m in clean_memories: print(Fore.LIGHTMAGENTA_EX + f"    -> {m[:75]}...")

        episodes = self.archivist.recall_episodes(
            search_query,
            n=3 if explicit_recall else 1,
            threshold=0.8 if explicit_recall else 0.55
        )

        if episodes:
            episodic_context = "\n".join(episodes)
            print(Fore.MAGENTA + f" [ARCHIVIST] Retrieved {len(episodes)} past sessions:")
            for e in episodes: print(Fore.LIGHTMAGENTA_EX + f"    -> {e[:75]}...")

        # Fetch live hardware vitals
        try:
            vitals = self.interoception.get_vitals()
            vitals_text = f"[LIVE SYSTEM VITALS]\n- CPU Usage: {int(vitals['cpu_percent'])}%\n- RAM Usage: {int(vitals['ram_percent'])}%\n- Disk Usage: {int(vitals['disk_percent'])}%"
        except:
            vitals_text = "[LIVE SYSTEM VITALS]\n- Offline"

        awareness_context = f"{self.chronometer.get_time_context()}\n\n{vitals_text}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": awareness_context}
        ]

        # ── PATCH: Session anchor injection ───────────────────────────────────
        # Injected early in messages so the LLM sees it before short-term memory
        # The explicit instruction prevents the LLM from overriding it with STM guesses
        if self.session_first_input:
            messages.append({
                "role": "system",
                "content": (
                    f"[SESSION ANCHOR] The very first thing the user said this session was: "
                    f"'{self.session_first_input}'. "
                    f"If the user asks what their first statement was, ALWAYS use this. "
                    f"Do not guess from conversation history."
                )
            })
        # ────────────────────────────────────────────────────────────────────────

        if episodic_context: messages.append({"role": "system", "content": f"[PAST EPISODES - Summaries]\n{episodic_context}"})
        if long_term_context: messages.append({"role": "system", "content": f"[LONG-TERM MEMORY - Facts]\n{long_term_context}"})
        for m in self.short_term_memory: messages.append({"role": "user" if m.startswith("User:") else "assistant", "content": m.split(":", 1)[1].strip()})
        messages.append({"role": "user", "content": user_input})

        # ── PATCH: IMAGINE mode hallucination guard ────────────────────────────
        if intent == "IMAGINE":
            messages.append({
                "role": "system",
                "content": (
                    "[IMAGINE MODE] You are hypothesizing a NOVEL idea right now. "
                    "Do NOT claim this connects to any past conversations unless that exact topic "
                    "appears verbatim in your [PAST EPISODES] context above. "
                    "Never say 'as per our previous discussions' or 'I recall suggesting' "
                    "unless it is explicitly in your provided context."
                )
            })
        # ────────────────────────────────────────────────────────────────────────

        full_response = ""
        for chunk in ollama.chat(model=self.model_name, messages=messages, stream=True, options={"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1}):
            full_response += chunk['message']['content']
            yield chunk

        # NOTE: No duplicate anchor setter here — anchor is set at the top of think()
        self.short_term_memory.extend([f"User: {user_input}", f"ATLAS: {full_response}"])
        self.session_history.extend([f"User: {user_input}", f"ATLAS: {full_response}"])
        self.last_interaction = {"user": user_input, "atlas": full_response}
        self._extract_facts(user_input)
