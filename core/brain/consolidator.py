import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import ollama
from colorama import Fore
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
        """Retrieve all memories with their IDs and embeddings"""
        if self.collection.count() == 0:
            return [], [], []
        
        results = self.collection.get(
            include=["documents", "embeddings"]
        )
        
        return (
            results['ids'],
            results['documents'],
            results['embeddings']
        )
    
    def cluster_memories(self, embeddings: list, threshold: float = 0.5) -> list:
        if len(embeddings) < 2:
            return [0] * len(embeddings)
        
        X = np.array(embeddings)
        
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=threshold,
            metric='cosine',
            linkage='average'
        )
        
        labels = clustering.fit_predict(X)
        return labels.tolist()
    
    def summarize_cluster(self, memories: list) -> str:
        if len(memories) == 1:
            return memories[0]
        
        memories_text = "\n".join(f"- {m}" for m in memories)
        
        prompt = f"""Combine these related facts about the user into ONE concise statement.
Keep all important information but remove redundancy.
Write in third person ("The user..." or "Sir...").
Maximum 50 words.

Facts:
{memories_text}

Combined statement:"""

        try:
            response = ollama.generate(model=self.model_name, prompt=prompt)
            return response['response'].strip()
        except Exception as e:
            print(Fore.RED + f" [CONSOLIDATOR] Summarization failed: {e}")
            return memories[0]  
    
    def consolidate(self, min_cluster_size: int = 2, threshold: float = 0.5) -> dict:
        print(Fore.CYAN + " [CONSOLIDATOR] Starting memory consolidation...")
        
        ids, documents, embeddings = self.get_all_memories()
        
        if len(documents) < min_cluster_size:
            print(Fore.YELLOW + " [CONSOLIDATOR] Not enough memories to consolidate")
            return {"consolidated": 0, "remaining": len(documents)}
        
        print(Fore.CYAN + f" [CONSOLIDATOR] Analyzing {len(documents)} memories...")
        
        labels = self.cluster_memories(embeddings, threshold)
        
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = {"ids": [], "docs": []}
            clusters[label]["ids"].append(ids[idx])
            clusters[label]["docs"].append(documents[idx])
        
        consolidated_count = 0
        
        for label, cluster in clusters.items():
            if len(cluster["docs"]) >= min_cluster_size:
                print(Fore.CYAN + f" [CONSOLIDATOR] Consolidating cluster of {len(cluster['docs'])} memories...")
                
                summary = self.summarize_cluster(cluster["docs"])
                
                if summary and len(summary) > 10:
                    self.collection.delete(ids=cluster["ids"])
                    
                    vector = self.embedder.encode(summary).tolist()
                    self.collection.add(
                        documents=[summary],
                        embeddings=[vector],
                        ids=[str(uuid.uuid4())],
                        metadatas=[{"consolidated": True, "source_count": len(cluster["docs"])}]
                    )
                    
                    print(Fore.GREEN + f" [CONSOLIDATOR] Created: {summary[:60]}...")
                    consolidated_count += len(cluster["docs"])
        
        remaining = self.collection.count()
        
        print(Fore.GREEN + f" [CONSOLIDATOR] Done! Consolidated {consolidated_count} memories into summaries")
        print(Fore.GREEN + f" [CONSOLIDATOR] Memory count: {len(documents)} → {remaining}")
        
        return {
            "original": len(documents),
            "consolidated": consolidated_count,
            "remaining": remaining
        }



if __name__ == "__main__":
    print("\n" + "="*50)
    print(" CONSOLIDATOR TEST")
    print("="*50)
    
    # Create test memories
    from memory import MemorySystem
    
    mem = MemorySystem(db_path="./test_consolidator")
    mem.clear_all()
    
    # Add fragmented memories
    test_memories = [
        "User likes Python",
        "User prefers Python over Java",
        "User is a Python developer",
        "User likes coffee",
        "User drinks espresso",
        "User prefers dark roast coffee",
        "User works on AI projects",
        "User is building a local AI assistant",
        "User is interested in machine learning"
    ]
    
    print("\n[TEST] Adding fragmented memories...")
    for m in test_memories:
        mem.save_memory(m)
        print(f"  Added: {m}")
    
    print(f"\n[TEST] Memory count before: {mem.collection.count()}")
    
    # Run consolidation
    consolidator = Consolidator(db_path="./test_consolidator")
    stats = consolidator.consolidate(min_cluster_size=2, threshold=0.6)
    
    print(f"\n[TEST] Memory count after: {stats['remaining']}")
    
    print("\n[TEST] Consolidated memories:")
    for m in mem.list_memories():
        print(f"  → {m}")