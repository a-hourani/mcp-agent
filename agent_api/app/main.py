# app/main.py
import json, asyncio
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse
from uuid import UUID
from app.schemas import QueryRequest, SSEEvent
from app.db import get_or_create_chat, init_db
from app.agent import run_agent_stream

app = FastAPI(title="LangGraph-MCP FastAPI Demo")

@app.on_event("startup")
async def startup_event():
    # create tables exactly once when the server boots
    await init_db()

def format_sse(data: dict) -> str:
    """Encode a dict as a single Server-Sent-Event line."""
    return f"data: {json.dumps(data, default=str)}\n\n"

@app.post("/query", response_model=None)
async def query(req: QueryRequest):
    chat_id: UUID = await get_or_create_chat(req.chat_id)

    async def event_generator():
        async for event in run_agent_stream(chat_id, req.message):
            yield format_sse(event)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",       # nginx friendliness
    }
    return StreamingResponse(event_generator(), headers=headers)
