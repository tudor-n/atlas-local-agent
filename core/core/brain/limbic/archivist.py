import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid
import ollama
from colorama import Fore

class Archivist:
    def __init__(self, db_path="./atlas_memory", model_name="llama3.1:latest"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.model_name = model_name
        self.episodes = self.client.get_or_create_collection(name="episodes", metadata={"hnsw:space": "cosine"})

    def summarize_session(self, conversation: list) -> str:
        if not conversation: return ""
        prompt = (
            "Summarize this conversation strictly based on facts. Focus on topics, decisions, tasks, and user facts.\n"
            "Keep it under 150 words, past tense, using bullet points.\n"
            "CRITICAL: Do NOT include meta-commentary about ATLAS being an AI, 'design limitations', or system constraints. Record only what was discussed.\n"
            f"Conversation:\n{chr(10).join(conversation)}\nSummary:"
        )
        try:
            return ollama.generate(model=self.model_name, prompt=prompt)['response'].strip()
        except Exception as e:
            print(Fore.RED + f" [ARCHIVIST] Failed to generate summary: {e}")
            return ""
        
    def archive_session(self, conversation: list, session_start: datetime) -> bool:
        if len(conversation) < 4: 
            print(Fore.YELLOW + " [ARCHIVIST] Session too short to archive (Needs at least 2 turns).")
            return False
        
        print(Fore.CYAN + " [ARCHIVIST] Processing session summary via LLM...")
        summary = self.summarize_session(conversation)
        if not summary or len(summary) < 20: 
            print(Fore.YELLOW + " [ARCHIVIST] Summary generation failed or was too short.")
            return False
        
        timestamp = session_start.strftime("%Y-%m-%d %H:%M")
        episode = f"[{timestamp}] {summary}"
        
        self.episodes.add(
            documents=[episode],
            embeddings=[self.embedder.encode(episode).tolist()],
            ids=[str(uuid.uuid4())],
            metadatas=[{"date": session_start.strftime("%Y-%m-%d"), "timestamp": timestamp, "type": "session"}]
        )
        print(Fore.GREEN + f" [ARCHIVIST] Session archived successfully: {summary[:60]}...")
        return True
    
    def recall_episodes(self, query: str, n: int = 3, threshold: float = 0.8) -> list:
        if self.episodes.count() == 0: return []
        results = self.episodes.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=min(n, self.episodes.count()),
            include=["documents", "distances", "metadatas"]
        )
        return [doc for doc, dist in zip(results['documents'][0], results['distances'][0]) if dist < threshold]