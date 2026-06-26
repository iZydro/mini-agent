from fastapi import FastAPI
from pydantic import BaseModel
from agent import create_initial_messages, run_agent
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

sessions = {}


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
    answer = run_agent(messages, request.message)

    return {
        "session_id": request.session_id,
        "answer": answer
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

