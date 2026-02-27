from core.brain.cognition.memory import MemorySystem

mem = MemorySystem()

BAD_ID = "89b1c998-0729-4efd-a760-cc676661ebf0"

print(f"Memories before: {mem.collection.count()}")
mem.collection.delete(ids=[BAD_ID])
print(f"Memories after:  {mem.collection.count()}")
print("Done. Corrupted memory purged.")
