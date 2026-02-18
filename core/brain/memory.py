import chromadb
from sentence_transformers import SentenceTransformer
import uuid
from colorama import Fore

class MemorySystem:
    def __init__(self, db_path="./atlas_memory"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(
            name="atlas_long_term",
            metadata={"hnsw:space": "cosine"}
        )
        print(f" [MEMORY] Loaded {self.collection.count()} memories from storage")

    def save_memory(self, text):
        if self.collection.count() > 0:
            existing = self.recall(text, n_results=1, similarity_threshold=0.3)
            if existing:
                return False
        
        vector = self.embedder.encode(text).tolist()
        self.collection.add(
            documents=[text],
            embeddings=[vector],
            ids=[str(uuid.uuid4())]
        )
        return True

    def recall(self, query, n_results=2, similarity_threshold=0.7):
        if self.collection.count() == 0:
            return []
        
        query_vector = self.embedder.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "distances"]
        )
        
        documents = results['documents'][0] if results['documents'] else []
        distances = results['distances'][0] if results.get('distances') else []
        
        filtered = [doc for doc, dist in zip(documents, distances) if dist < similarity_threshold]
        
        return filtered

    def forget(self, query, threshold=0.3):
        if self.collection.count() == 0:
            return False
        
        query_vector = self.embedder.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=1,
            include=["documents", "distances"]
        )
        
        if not results['documents'] or not results['documents'][0]:
            return False
        
        distance = results['distances'][0][0]
        document = results['documents'][0][0]
        
        if distance > threshold:
            return False
        
        match = self.collection.get(
            where_document={"$contains": document[:50]}
        )
        
        if match['ids']:
            self.collection.delete(ids=[match['ids'][0]])
            print(Fore.RED + f" [MEMORY] Forgot: {document[:50]}...")
            return True
        
        return False

    def list_memories(self, limit=10):
        if self.collection.count() == 0:
            return []
        results = self.collection.peek(limit=limit)
        return results['documents'] if results else []

    def clear_all(self):
        self.client.delete_collection("atlas_long_term")
        self.collection = self.client.get_or_create_collection(
            name="atlas_long_term",
            metadata={"hnsw:space": "cosine"}
        )
        print(Fore.RED + " [MEMORY] All memories wiped")