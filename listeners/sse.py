from queue import Queue


class SseListener:
    def __init__(self):
        self.queues = {}

    def subscribe(self, session_id):
        queue = Queue()
        self.queues.setdefault(session_id, []).append(queue)
        return queue

    def unsubscribe(self, session_id, queue):
        if session_id not in self.queues:
            return

        self.queues[session_id] = [
            q for q in self.queues[session_id]
            if q is not queue
        ]

        if not self.queues[session_id]:
            del self.queues[session_id]

    def on_event(self, event):
        session_id = event.get("session_id")

        for queue in self.queues.get(session_id, []):
            queue.put(event)
