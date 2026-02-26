from core.brain.limbic.archivist import Archivist
from core.brain.limbic.consolidator import Consolidator
from datetime import datetime

class SleepSystem:
    def __init__(self, db_path="./atlas_memory", model_name="llama3.1:latest"):
        self.archivist = Archivist(db_path=db_path, model_name=model_name)
        self.consolidator = Consolidator(db_path=db_path, model_name=model_name)
    
    def sleep(self, conversation: list, session_start: datetime, consolidate: bool = True) -> dict:
        stats = {
            "session_archived": self.archivist.archive_session(conversation, session_start),
            "consolidation": None
        }
        if consolidate:
            # Increased threshold to 0.85 so it aggressively groups related facts!
            stats["consolidation"] = self.consolidator.consolidate(min_cluster_size=2, threshold=0.85)
        return stats