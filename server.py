from fastapi import FastAPI
from listeners.sse import SseListener
from pydantic import BaseModel
from agent import create_initial_messages, run_agent
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import json
from core.event_bus import EventBus
from listeners.console import ConsoleListener
from listeners.transcript import TranscriptListener
from listeners.sse import SseListener
from transcript import Transcript

app = FastAPI()

sessions = {}
events = EventBus()
sse = SseListener()

events.register(ConsoleListener(
    enabled=True,
    show_results=False
))

events.register(
    TranscriptListener(
        Transcript()
    )
)

events.register(sse)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    if request.session_id not in sessions:
        sessions[request.session_id] = create_initial_messages()

    messages = sessions[request.session_id]
    answer = run_agent(
        messages,
        request.message,
        events,
        request.session_id
    )

    return {
        "session_id": request.session_id,
        "answer": answer
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


def event_stream():

    while True:

        event = sse.queue.get()

        yield f"data: {json.dumps(event)}\n\n"


@app.get("/api/events/{session_id}")
def stream_events(session_id: str):
    queue = sse.subscribe(session_id)

    def event_stream():
        try:
            while True:
                event = queue.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            sse.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
