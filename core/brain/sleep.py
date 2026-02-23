from core.brain.archivist import Archivist
from core.brain.consolidator import Consolidator
from datetime import datetime
from colorama import Fore


class SleepSystem:
    
    def __init__(self, db_path="./atlas_memory", model_name="llama3.1:latest"):
        self.archivist = Archivist(db_path=db_path, model_name=model_name)
        self.consolidator = Consolidator(db_path=db_path, model_name=model_name)
        self.db_path = db_path
        self.model_name = model_name
    
    def sleep(self, conversation: list, session_start: datetime, consolidate: bool = True) -> dict:
        print(Fore.CYAN + "\n" + "="*50)
        print(Fore.CYAN + " [SLEEP] ATLAS entering sleep cycle...")
        print(Fore.CYAN + "="*50)
        
        stats = {
            "session_archived": False,
            "consolidation": None
        }
        
        print(Fore.CYAN + "\n [SLEEP] Step 1: Archiving session...")
        stats["session_archived"] = self.archivist.archive_session(
            conversation, 
            session_start
        )

        if consolidate:
            print(Fore.CYAN + "\n [SLEEP] Step 2: Consolidating memories...")
            stats["consolidation"] = self.consolidator.consolidate(
                min_cluster_size=3,
                threshold=0.5
            )
        
        print(Fore.GREEN + "\n" + "="*50)
        print(Fore.GREEN + " [SLEEP] Sleep cycle complete. Sweet dreams, Sir.")
        print(Fore.GREEN + "="*50 + "\n")
        
        return stats


# =============================================================================
# STANDALONE SLEEP SCRIPT
# =============================================================================

def run_sleep_cycle():
    """
    Standalone function to run consolidation without a session.
    Can be run as a cron job or scheduled task.
    """
    print(Fore.CYAN + " [SLEEP] Running standalone memory consolidation...")
    
    consolidator = Consolidator()
    stats = consolidator.consolidate(min_cluster_size=2, threshold=0.5)
    
    print(Fore.GREEN + f" [SLEEP] Consolidation complete: {stats}")


if __name__ == "__main__":
    run_sleep_cycle()