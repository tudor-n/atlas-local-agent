from pathlib import Path

class Perception:
    def __init__(self, bus):
        self.bus = bus

    def ingest_file(self, filepath: str) -> str:
        try:
            content = Path(filepath).read_text(encoding='utf-8')
            self.bus.publish("file_ingested", {"path": filepath, "size": len(content)})
            return content
        except Exception as e:
            self.bus.publish("perception_error", str(e))
            return ""