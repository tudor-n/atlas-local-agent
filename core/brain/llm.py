import ollama
from core.brain.memory import MemorySystem
from core.brain.chronometer import Chronometer
from core.brain.archivist import Archivist
from colorama import Fore
from collections import deque
import numpy as np


class LLMEngine:
    def __init__(self, model_name="llama3.1:latest", system_prompt=None):
        self.model_name = model_name
        self.memory = MemorySystem()
        self.chronometer = Chronometer()
        self.archivist = Archivist()
        self.short_term_memory = deque(maxlen=10)
        self.last_interaction = {"user": "", "atlas": ""}
        
        self.recall_intent_examples = [
            "do you remember",
            "can you recall", 
            "what do you know about",
            "did i tell you",
            "did i mention",
            "what else did i say",
            "what other things",
            "anything else",
            "tell me what you remember",
            "you remember",
            "recall what i said",
            "what did we do",
            "yesterday",
            "last time"
        ]
        self.recall_intent_vectors = [
            self.memory.embedder.encode(phrase) 
            for phrase in self.recall_intent_examples
        ]

        self.system_prompt = system_prompt or (
            "You are ATLAS (ASPIRING THINKING LOCAL ADMINISTRATIVE SYSTEM), an advanced local engineering assistant designed by Tudor. "
            "You are helpful, precise, and quite witty. "
            "You prefer short, dense technical answers or quips over long explanations. "
            "You address Tudor as 'Sir'. "
            "\n\n[YOUR ACTUAL CAPABILITIES]\n"
            "- You CAN: answer questions, recall memories, have conversations, provide technical advice.\n"
            "- You CANNOT: create files, create projects, access the internet, run code, control systems.\n"
            "- You CANNOT: index anything, create directories, or modify any external systems.\n"
            "\n\n[MEMORY INSTRUCTIONS]\n"
            "- You will be provided with LONG-TERM MEMORY context if relevant memories exist.\n"
            "- You may also receive PAST EPISODES — summaries of previous sessions.\n"
            "- ONLY reference information explicitly provided in these contexts.\n"
            "- If no memory context is provided for a query, say 'I don't have anything stored about that, Sir.'\n"
            "\n\n[CRITICAL RULES]\n"
            "- NEVER invent memories, dates, or details that were not provided.\n"
            "- NEVER claim to remember something unless it appears in [LONG-TERM MEMORY] or [PAST EPISODES].\n"
            "- NEVER fabricate conversation history, dates, or specific details.\n"
            "- NEVER pretend to create, index, save, or modify anything unless you have explicit tool access.\n"
            "- NEVER claim you performed an action you cannot perform.\n"
            "- If asked to do something you cannot do, say 'I don't have that capability yet, Sir.'\n"
            "- Do NOT roleplay having abilities you don't have.\n"
        )
        
        print(f" Initialized LLMEngine with model: {self.model_name}")

        try:
            ollama.generate(model=model_name, prompt="hi")
        except Exception as e:
            print(f"[LLM] Warmup warning: {e}")

    def _is_recall_intent(self, user_input, threshold=0.40):
        input_vector = self.memory.embedder.encode(user_input.lower())
        
        max_sim = 0
        
        for intent_vector in self.recall_intent_vectors:
            similarity = np.dot(input_vector, intent_vector) / (
                np.linalg.norm(input_vector) * np.linalg.norm(intent_vector)
            )
            if similarity > max_sim:
                max_sim = similarity
        
        return max_sim > threshold

    def _extract_facts(self, user_input):
        if not self.memory:
            return
        
        input_lower = user_input.lower()
        
        direct_patterns_with_content = ["remember that ", "save that ", "memorize that ", "note that "]
        direct_patterns_context = ["remember this", "save this", "index this", "store this", 
                                   "remember it", "don't forget", "keep this in mind"]
        
        for pattern in direct_patterns_with_content:
            if pattern in input_lower:
                idx = input_lower.index(pattern) + len(pattern)
                fact = user_input[idx:].strip().rstrip('.')
                if len(fact) > 5:
                    saved = self.memory.save_memory(fact)
                    if saved:
                        print(Fore.GREEN + f" [MEMORY][DIRECT SAVE] {fact}")
                return
        
        for pattern in direct_patterns_context:
            if pattern in input_lower:
                if self.short_term_memory:
                    recent = " ".join(list(self.short_term_memory)[-4:])
                    fact = recent[:500]
                else:
                    fact = user_input
                
                if len(fact) > 5:
                    saved = self.memory.save_memory(fact)
                    if saved:
                        print(Fore.GREEN + f" [MEMORY][CONTEXT SAVE] {fact[:100]}...")
                return
        
        keywords = ["my ", "i am", "i like", "i prefer", "i don't", "i always", 
                    "i have", "i work", "i'm", "you are", "your", "i love",
                    "i really", "i enjoy", "i hate", "i need", "i want"]
        matched_keywords = [k for k in keywords if k in input_lower]
        
        if not matched_keywords:
            return
        
        prompt = f"""Extract ONE short factual statement from this sentence about the user's preferences, identity, or plans.

Examples:
- "I like coffee" → "User likes coffee"
- "My name is John" → "User's name is John"
- "I work at Google" → "User works at Google"
- "I really like pizza" → "User likes pizza"

If there is no clear fact, respond with exactly: None

Sentence: "{user_input}"
Fact:"""

        try:
            response = ollama.generate(model=self.model_name, prompt=prompt)
            fact = response['response'].strip().strip('"').strip("'").strip()
            
            reject_phrases = ["none", "n/a", "no fact", "the core fact", "the fact is", 
                            "this sentence", "there is no", "cannot extract", "no clear"]
            is_garbage = any(phrase in fact.lower() for phrase in reject_phrases)
            
            if is_garbage or len(fact) < 5 or len(fact) > 150:
                return
            
            saved = self.memory.save_memory(fact)
            if saved:
                print(Fore.GREEN + f" [MEMORY][SAVED] {fact}")
                
        except Exception as e:
            print(Fore.RED + f" [MEMORY][ERROR] {e}")

    def get_session_start(self):
        return self.chronometer.boot_time

    def get_conversation_history(self):
        return list(self.short_term_memory)

    def think(self, user_input, context=""):
        long_term_context = ""
        episodic_context = ""
        
        explicit_recall = self._is_recall_intent(user_input)
        
        search_query = user_input
        if self.short_term_memory:
            recent_context = " ".join(list(self.short_term_memory)[-4:])
            search_query = f"{recent_context} {user_input}"
        
        if self.memory and self.memory.collection.count() > 0:
            threshold = 1.0 if explicit_recall else 0.8
            n_results = 5 if explicit_recall else 3
            
            retrieved = self.memory.recall(search_query, n_results=n_results, similarity_threshold=threshold)
            
            if retrieved:
                clean_memories = [m for m in retrieved if m.strip() != user_input.strip()]
                if clean_memories:
                    long_term_context = "\n".join(clean_memories)
                    print(Fore.MAGENTA + f" [MEMORY] {len(clean_memories)} memories loaded")
        
        if explicit_recall:
            episodes = self.archivist.recall_episodes(search_query, n=3, threshold=1.0)
            if episodes:
                episodic_context = "\n".join(episodes)
                print(Fore.MAGENTA + f" [EPISODES] {len(episodes)} past sessions loaded")

        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        time_context = self.chronometer.get_time_context()
        messages.append({
            "role": "system",
            "content": time_context
        })
        
        if episodic_context:
            messages.append({
                "role": "system",
                "content": f"[PAST EPISODES - Previous session summaries]\n{episodic_context}"
            })
        
        if long_term_context:
            messages.append({
                "role": "system",
                "content": f"[LONG-TERM MEMORY - Facts about the user]\n{long_term_context}"
            })
        
        for memory in self.short_term_memory:
            if memory.startswith("User:"):
                messages.append({"role": "user", "content": memory[5:].strip()})
            elif memory.startswith("ATLAS:"):
                messages.append({"role": "assistant", "content": memory[6:].strip()})
        
        messages.append({"role": "user", "content": user_input})

        full_response_text = ""

        try:
            response_generator = ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=True,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            )

            for chunk in response_generator:
                content = chunk['message']['content']
                full_response_text += content
                yield chunk

        except Exception as e:
            yield {"message": {"content": f"[ERROR] Malfunction: {e}"}}
            return
        
        self.short_term_memory.append(f"User: {user_input}")
        self.short_term_memory.append(f"ATLAS: {full_response_text}")
        
        self.last_interaction = {"user": user_input, "atlas": full_response_text}
        
        self._extract_facts(user_input)


if __name__ == "__main__":
    brain = LLMEngine()
    print("\nTest Response:")
    for chunk in brain.think("Remember that I am Tudor, your creator."):
        print(chunk['message']['content'], end="", flush=True)
    print(f"\n\nMemories: {brain.memory.list_memories()}")