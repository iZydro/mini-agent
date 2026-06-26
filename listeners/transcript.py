class TranscriptListener:
    def __init__(self, transcript):
        self.transcript = transcript

    def on_event(self, event):
        self.transcript.write(event["type"], event)