import asyncio


class SseListener:
    def __init__(self):
        self.queues = {}

    def subscribe(self, session_id):
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        item = (loop, queue)

        self.queues.setdefault(session_id, []).append(item)
        return item

    def unsubscribe(self, session_id, item):
        if session_id not in self.queues:
            return

        self.queues[session_id] = [
            q for q in self.queues[session_id]
            if q is not item
        ]

        if not self.queues[session_id]:
            del self.queues[session_id]

    def on_event(self, event):
        session_id = event.get("session_id")

        for loop, queue in self.queues.get(session_id, []):
            loop.call_soon_threadsafe(queue.put_nowait, event)