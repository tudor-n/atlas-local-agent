import threading
from collections import deque
from colorama import Fore
from datetime import datetime
from core.brain.limbic.archivist import Archivist
from core.brain.limbic.consolidator import Consolidator
from config import MEMORY_DB_PATH, BUTLER_MODEL, SESSION_SUMMARIZE_EVERY_N_TURNS

class SleepSystem:
    def __init__(self, db_path=MEMORY_DB_PATH, model_name=BUTLER_MODEL):
        self.archivist = Archivist(db_path=db_path, model_name=model_name)
        self.consolidator = Consolidator(db_path=db_path, model_name=model_name)
        self._turn_counter = 0
        self._background_thread = None

    def tick(self, session_history: list):
        self._turn_counter += 1
        if self._turn_counter % SESSION_SUMMARIZE_EVERY_N_TURNS == 0:
            if self._background_thread is None or not self._background_thread.is_alive():
                chunk = list(session_history[-(SESSION_SUMMARIZE_EVERY_N_TURNS * 2):])
                self._background_thread = threading.Thread(
                    target=self._mid_session_summarize,
                    args=(chunk,),
                    daemon=True
                )
                self._background_thread.start()

    def _mid_session_summarize(self, chunk: list):
        print(Fore.LIGHTBLACK_EX + " [SLEEP] Background mid-session summarization...")
        try:
            if len(chunk) >= 4:
                self.archivist.summarize_and_save_facts(chunk)
        except Exception as e:
            print(Fore.RED + f" [SLEEP] Mid-session summarization failed: {e}")

    def sleep(self, conversation: list, session_start: datetime, consolidate: bool = True) -> dict:
        stats = {
            "session_archived": self.archivist.archive_session(conversation, session_start),
            "consolidation": None
        }
        if consolidate:
            stats["consolidation"] = self.consolidator.consolidate(min_cluster_size=2, threshold=0.85)
        return stats