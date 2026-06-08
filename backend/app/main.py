from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import handle_chat


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(default="default")
    messages: list[ChatMessage]
    current_flow: str | None = None


class ChatResponse(BaseModel):
    role: str
    content: str
    flow: str
    sources: list[dict] = []
    suggested_replies: list[str] = []


app = FastAPI(title="PartSelect Chat Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    messages = [message.model_dump() for message in request.messages]
    result = handle_chat(messages, request.current_flow)
    return result.to_dict()
