import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid
import ollama
from colorama import Fore
from config import MEMORY_DB_PATH, BUTLER_MODEL

class Archivist:
    def __init__(self, db_path=MEMORY_DB_PATH, model_name=BUTLER_MODEL):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.model_name = model_name
        self.episodes = self.client.get_or_create_collection(name="episodes", metadata={"hnsw:space": "cosine"})

    def summarize_session(self, conversation: list) -> str:
        if not conversation: return ""
        prompt = (
            "Summarize this conversation. Focus on topics, decisions, tasks, user facts.\n"
            "Max 150 words. Past tense. Bullet points. No meta-commentary about AI.\n"
            f"Conversation:\n{chr(10).join(conversation)}\nSummary:"
        )
        try:
            return ollama.generate(model=self.model_name, prompt=prompt, options={"num_predict": 300})['response'].strip()
        except Exception as e:
            print(Fore.RED + f" [ARCHIVIST] Summary failed: {e}")
            return ""

    def summarize_and_save_facts(self, conversation: list):
        from core.brain.cognition.memory import MemorySystem
        mem = MemorySystem()
        prompt = (
            "Extract up to 5 standalone factual statements about the user or their projects from this conversation.\n"
            "Output ONLY a JSON array of strings. No explanation.\n"
            "Example: [\"User is building an AI assistant called ATLAS\", \"User prefers Python for scripting\"]\n"
            f"Conversation:\n{chr(10).join(conversation[-20:])}\nFacts:"
        )
        try:
            import json, re
            response = ollama.generate(model=self.model_name, prompt=prompt, options={"num_predict": 300})['response'].strip()
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                facts = json.loads(match.group(0))
                for fact in facts:
                    if isinstance(fact, str) and 5 < len(fact) < 200:
                        if mem.save_memory(fact, importance=6.0, tags=["auto_extracted"]):
                            print(Fore.MAGENTA + f" [ARCHIVIST] Mid-session fact saved: {fact[:60]}")
        except Exception as e:
            print(Fore.RED + f" [ARCHIVIST] Fact extraction failed: {e}")

    def archive_session(self, conversation: list, session_start: datetime) -> bool:
        if len(conversation) < 4:
            return False
        summary = self.summarize_session(conversation)
        if not summary or len(summary) < 20:
            return False
        timestamp = session_start.strftime("%Y-%m-%d %H:%M")
        episode = f"[{timestamp}] {summary}"
        self.episodes.add(
            documents=[episode],
            embeddings=[self.embedder.encode(episode).tolist()],
            ids=[str(uuid.uuid4())],
            metadatas=[{"date": session_start.strftime("%Y-%m-%d"), "timestamp": timestamp, "type": "session"}]
        )
        print(Fore.GREEN + f" [ARCHIVIST] Session archived: {summary[:60]}...")
        return True

    def recall_episodes(self, query: str, n: int = 3, threshold: float = 0.40) -> list: 
        if self.episodes.count() == 0: return []
        
        results = self.episodes.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=min(n, self.episodes.count()),
            include=["documents", "distances"]
        )
        
        valid_episodes = []
        for doc, dist in zip(results['documents'][0], results['distances'][0]):
            if dist < threshold:
                valid_episodes.append(doc)
                
        return valid_episodes