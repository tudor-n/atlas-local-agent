import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import ollama
import uuid

class Consolidator:    
    def __init__(self, db_path="./atlas_memory", model_name="llama3.1:latest"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.model_name = model_name
        self.collection = self.client.get_or_create_collection(
            name="atlas_long_term",
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_all_memories(self) -> tuple:
        if self.collection.count() == 0: return [], [], []
        results = self.collection.get(include=["documents", "embeddings"])
        return results['ids'], results['documents'], results['embeddings']
    
    def cluster_memories(self, embeddings: list, threshold: float = 0.5) -> list:
        if len(embeddings) < 2: return [0] * len(embeddings)
        clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=threshold, metric='cosine', linkage='average')
        return clustering.fit_predict(np.array(embeddings)).tolist()
    
    def summarize_cluster(self, memories: list) -> str:
        if len(memories) == 1: return memories[0]
        prompt = f"Combine these related facts about the user into ONE concise statement.\nMaximum 50 words, third person.\nFacts:\n{chr(10).join(f'- {m}' for m in memories)}\nCombined statement:"
        try:
            return ollama.generate(model=self.model_name, prompt=prompt)['response'].strip()
        except:
            return memories[0]  
    
    def consolidate(self, min_cluster_size: int = 2, threshold: float = 0.5) -> dict:
        ids, documents, embeddings = self.get_all_memories()
        if len(documents) < min_cluster_size:
            return {"consolidated": 0, "remaining": len(documents)}
        
        clusters = {}
        for idx, label in enumerate(self.cluster_memories(embeddings, threshold)):
            clusters.setdefault(label, {"ids": [], "docs": []})
            clusters[label]["ids"].append(ids[idx])
            clusters[label]["docs"].append(documents[idx])
        
        consolidated_count = 0
        for label, cluster in clusters.items():
            if len(cluster["docs"]) >= min_cluster_size:
                summary = self.summarize_cluster(cluster["docs"])
                if summary and len(summary) > 10:
                    self.collection.delete(ids=cluster["ids"])
                    self.collection.add(
                        documents=[summary],
                        embeddings=[self.embedder.encode(summary).tolist()],
                        ids=[str(uuid.uuid4())],
                        metadatas=[{"consolidated": True, "source_count": len(cluster["docs"])}]
                    )
                    consolidated_count += len(cluster["docs"])
        
        return {"original": len(documents), "consolidated": consolidated_count, "remaining": self.collection.count()}