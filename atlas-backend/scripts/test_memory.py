from core.brain.cognition.memory import MemorySystem

mem = MemorySystem(db_path="./atlas_memory")  # Same path as main.py

print(f"Total memories: {mem.collection.count()}")
print(f"Stored: {mem.list_memories()}")

# Test recall with the exact query ATLAS received
test_queries = [
    "Do you remember who I am?",
    "Who is Tudor?",
    "Who created you?",
    "developer"
]

for q in test_queries:
    result = mem.recall(q, n_results=2, similarity_threshold=1.5)
    print(f"\nQuery: '{q}'")
    print(f"Result: {result}")