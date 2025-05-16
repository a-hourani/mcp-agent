# app/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, Any

class QueryRequest(BaseModel):
    message: str = Field(..., example="Add 111 and 222, use the tool.")
    chat_id: Optional[UUID] = None      # may be omitted

class SSEEvent(BaseModel):
    type: str               # thought / tool_call / tool_result / final
    data: Any
    chat_id: UUID
