import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid
from config import MEMORY_DB_PATH

class MemorySystem:
    def __init__(self, db_path=MEMORY_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(
            name="atlas_long_term",
            metadata={"hnsw:space": "cosine"}
        )

    def save_memory(self, text: str, importance: float = 5.0, tags: list = None) -> bool:
        if self.collection.count() > 0 and self.recall(text, n_results=1, similarity_threshold=0.25):
            return False
        self.collection.add(
            documents=[text],
            embeddings=[self.embedder.encode(text).tolist()],
            ids=[str(uuid.uuid4())],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "importance": importance,
                "tags": ",".join(tags or []),
                "confirmed": True,
            }]
        )
        return True

    def recall(self, query: str, n_results: int = 2, similarity_threshold: float = 0.7) -> list:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "distances", "metadatas"]
        )
        docs = results['documents'][0] if results['documents'] else []
        dists = results['distances'][0] if results.get('distances') else []
        metas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(docs)
        filtered = [(doc, meta) for doc, dist, meta in zip(docs, dists, metas) if dist < similarity_threshold]
        filtered.sort(key=lambda x: float(x[1].get("importance", 5.0)), reverse=True)
        return [doc for doc, _ in filtered]

    def forget(self, query: str, threshold: float = 0.3) -> bool:
        if self.collection.count() == 0:
            return False
        results = self.collection.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=1,
            include=["documents", "distances"]
        )
        if not results['documents'] or not results['documents'][0]:
            return False
        if results['distances'][0][0] > threshold:
            return False
        match = self.collection.get(where_document={"$contains": results['documents'][0][0][:50]})
        if match['ids']:
            self.collection.delete(ids=[match['ids'][0]])
            return True
        return False