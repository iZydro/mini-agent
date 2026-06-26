from datetime import datetime


class EventBus:
    def __init__(self):
        self.listeners = []

    def register(self, listener):
        self.listeners.append(listener)

    def emit(self, session_id, event_type, **data):
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "type": event_type,
            **data
        }

        for listener in self.listeners:
            listener.on_event(event)
