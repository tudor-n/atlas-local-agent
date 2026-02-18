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
        
        self.episodes = self.client.get_or_create_collection(
            name="episodes",
            metadata={"hnsw:space": "cosine"}
        )

        print(f" [ARCHIVIST] Loaded {self.episodes.count()} past episodes")

    def summarize_session(self, conversation: list) -> str:
        if not conversation:
            return ""
        
        full_conversation = "\n".join(conversation)
        prompt = f"""Summarize this conversation between a user (Tudor) and an AI assistant (ATLAS).
Focus on:
- What topics were discussed
- What was learned or decided
- Any tasks mentioned or completed
- Key facts revealed about the user

Keep it under 150 words. Write in past tense.
Do NOT include pleasantries or greetings.

Conversation:
{full_conversation}

Summary:"""
        
        try:
            response = ollama.generate(model=self.model_name, prompt=prompt)
            summary = response['response'].strip()
            return summary
        except Exception as e:
            print(Fore.RED + f" [ARCHIVIST] Summarization failed: {e}")
            return ""
        
    def archive_session(self, conversation: list, session_start: datetime) -> bool:
        if len(conversation) < 4:
            print(Fore.YELLOW + " [ARCHIVIST] Session too short to archive")
            return False
        
        print(Fore.CYAN + " [ARCHIVIST] Summarizing session...")

        summary = self.summarize_session(conversation)

        if not summary or len(summary) < 20:
            print(Fore.YELLOW + " [ARCHIVIST] Summary too short, skipping")
            return False
        
        timestamp = session_start.strftime("%Y-%m-%d %H:%M")
        date_str = session_start.strftime("%Y-%m-%d")

        episode = f"[{timestamp}] {summary}"

        vector = self.embedder.encode(episode).tolist()

        self.episodes.add(
            documents=[episode],
            embeddings=[vector],
            ids=[str(uuid.uuid4())],
            metadatas=[{
                "date": date_str,
                "timestamp": timestamp,
                "type": "session"
            }]
        )

        print(Fore.GREEN + f" [ARCHIVIST] Session archived: {summary[:60]}...")
        return True
    
    def recall_episodes(self, query: str, n: int = 3, threshold: float = 0.8) -> list:
        if self.episodes.count() == 0:
            return []
        
        query_vector = self.embedder.encode(query).tolist()

        results = self.episodes.query(
            query_embeddings=[query_vector],
            n_results=min(n, self.episodes.count()),
            include=["documents", "distances", "metadatas"]
        )

        episodes = []
        for doc, dist in zip(results['documents'][0], results['distances'][0]):
            if dist < threshold:
                episodes.append(doc)

        return episodes
    
    def recall_by_date(self, date_str: str) -> list:
        if self.episodes.count() == 0:
            return []
        
        results = self.episodes.get(
            where={"date": date_str},
            include=["documents"]
        )

        return results['documents'] if results['documents'] else []
    
    def get_recent_episodes(self, n: int = 5) -> list:
        if self.episodes.count() == 0:
            return []
        
        results = self.episodes.peek(limit=n)
        return results['documents'] if results else []
    
    def count(self) -> int:
        return self.episodes.count()


if __name__ == "__main__":
    print("\n" + "="*50)
    print(" ARCHIVIST TEST")
    print("="*50)
    
    archivist = Archivist(db_path="./test_archivist")
    
    test_conversation = [
        "User: Hey Atlas, let's work on the Mark 2 project today.",
        "ATLAS: Ready to assist with Mark 2, Sir. What's the focus?",
        "User: We need to fix the cooling system. It's overheating.",
        "ATLAS: Thermal throttling issue. Have you checked the fan curves?",
        "User: Good idea. Also, remember that I prefer Nvidia GPUs.",
        "ATLAS: Noted, Sir. Nvidia GPUs for future recommendations.",
        "User: Let's also debug that memory leak we found yesterday.",
        "ATLAS: I'll help trace the allocation patterns, Sir."
    ]
    
    print("\n[TEST] Archiving test session...")
    archivist.archive_session(test_conversation, datetime.now())
    
    print(f"\n[TEST] Total episodes: {archivist.count()}")
    
    print("\n[TEST] Recent episodes:")
    for ep in archivist.get_recent_episodes():
        print(f"  → {ep[:80]}...")
    
    print("\n[TEST] Recalling 'cooling system':")
    results = archivist.recall_episodes("cooling system problems", threshold=1.0)
    for r in results:
        print(f"  → {r[:80]}...")