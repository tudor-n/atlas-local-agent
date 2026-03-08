from collections import defaultdict

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type: str, callback):
        self.subscribers[event_type].append(callback)

    def publish(self, event_type: str, data=None):
        for callback in self.subscribers.get(event_type, []):
            callback(data)