class ToolContext:
    def __init__(self, events, session_id, tool_name):
        self.events = events
        self.session_id = session_id
        self.tool_name = tool_name

    def emit(self, event_type, **data):
        self.events.emit(
            self.session_id,
            event_type,
            tool=self.tool_name,
            **data
        )

    def info(self, message, **data):
        self.emit("tool_info", message=message, **data)

    def progress(self, message, **data):
        self.emit("tool_progress", message=message, **data)

    def api_call_start(self, api):
        self.emit("api_call_start", api=api)

    def api_call_end(self, api):
        self.emit("api_call_end", api=api)