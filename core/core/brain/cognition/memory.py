import chromadb
from sentence_transformers import SentenceTransformer
import uuid

class MemorySystem:
    def __init__(self, db_path="./atlas_memory"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(
            name="atlas_long_term",
            metadata={"hnsw:space": "cosine"}
        )

    def save_memory(self, text):
        if self.collection.count() > 0 and self.recall(text, n_results=1, similarity_threshold=0.3):
            return False
        
        self.collection.add(
            documents=[text],
            embeddings=[self.embedder.encode(text).tolist()],
            ids=[str(uuid.uuid4())]
        )
        return True

    def recall(self, query, n_results=2, similarity_threshold=0.7):
        if self.collection.count() == 0:
            return []
        
        results = self.collection.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "distances"]
        )
        
        docs = results['documents'][0] if results['documents'] else []
        dists = results['distances'][0] if results.get('distances') else []
        return [doc for doc, dist in zip(docs, dists) if dist < similarity_threshold]

    def forget(self, query, threshold=0.3):
        if self.collection.count() == 0: return False
        
        results = self.collection.query(
            query_embeddings=[self.embedder.encode(query).tolist()],
            n_results=1,
            include=["documents", "distances"]
        )
        
        if not results['documents'] or not results['documents'][0]: return False
        if results['distances'][0][0] > threshold: return False
        
        match = self.collection.get(where_document={"$contains": results['documents'][0][0][:50]})
        if match['ids']:
            self.collection.delete(ids=[match['ids'][0]])
            return True
        return False