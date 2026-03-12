from core.brain.cognition.memory import MemorySystem

mem = MemorySystem()
print(f"\nTotal memories: {mem.collection.count()}\n")

all_docs = mem.collection.get(include=["documents"])

for i, (doc_id, doc) in enumerate(zip(all_docs["ids"], all_docs["documents"])):
    print(f"[{i}] {doc[:120]}")
    print(f"     ID: {doc_id}")
    print()
















