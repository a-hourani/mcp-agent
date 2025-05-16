# app/agent.py   ── replace run_agent_stream with the version below
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from typing import Any, Dict, AsyncGenerator, List, Optional
from uuid import UUID
from app.db import save_message, fetch_history
from contextlib import asynccontextmanager
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient


_llm = ChatOpenAI(model="o3-mini")

@asynccontextmanager
async def agent_ctx():
    async with MultiServerMCPClient(
        {
            "mcp_server": {
                "url": "http://mcp-server:8000/sse",
                "transport": "sse"
            }
        }
    ) as client:
        agent = create_react_agent(
            _llm,
            tools=client.get_tools(),
            prompt="You are a helpful assistant."
        )
        yield agent

async def run_agent_stream(chat_id: UUID, user_msg: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streams every LangChain/LangGraph callback as dicts suitable for SSE,
    *and* stores the final assistant reply in SQLite.
    """
    # ---------- build prompt --------------------------------------------------
    past = await fetch_history(chat_id, limit=20)
    history_msgs: List[BaseMessage] = [
        HumanMessage(content=c) if r == "user" else AIMessage(content=c)
        for r, c in past
    ]
    history_msgs.append(HumanMessage(content=user_msg))

    await save_message(chat_id, "user", user_msg)

    # ---------- stream & capture ---------------------------------------------
    final_answer: Optional[str] = None        # we’ll fill this inside the loop

    async with agent_ctx() as agent:
        async for ev in agent.astream_events({"messages": history_msgs}):

            kind: str = ev["event"]
            data: Any = ev["data"]
            
            # if not isinstance(data, dict):
            #     print(type(data))
            #     data = data.json()

            if 'chunk' in data and not isinstance(data['chunk'], dict):
                data['chunk'] = data['chunk'].json()
            # if 'output' in data and not isinstance(data['output'], dict) and not isinstance():
            try:
                data['output'] = data['output'].json()
            except:
                pass
            # if 'chunk' in data and getattr(data['chunk'], 'content', None):
            #     print(type(data['chunk']))
            #     data['chunk'] = {'content': data['chunk'].content}

            # ─── Detect assistant completion ────────────────────────────────
            if kind in ("on_chat_model_end", "on_chain_end"):
                extracted = _extract_content(data.get("output", data))
                if extracted:
                    final_answer = extracted

            # ─── forward the raw event to the client -------------------------
            yield {
                "type": kind,
                "data": data,
                "chat_id": str(chat_id)
            }

    # ---------- after streaming finishes, persist assistant reply ---------
    if final_answer is not None:
        await save_message(chat_id, "assistant", final_answer)


# ---------------------------------------------------------------------------
def _extract_content(output: Any) -> Optional[str]:
    """
    Robustly pull the assistant text out of whatever LangChain gives us:
       • AIMessage          → .content
       • {"messages":[…]}   → tail.content
       • plain string       → itself
    Returns None if it can’t recognise the structure.
    """
    if output is None:
        return None

    # Case 1: already an AIMessage
    if isinstance(output, AIMessage):
        return output.content

    # Case 2: wrapper dict from chain_end  {"messages":[AIMessage]}
    if isinstance(output, dict) and "messages" in output:
        tail = output["messages"][-1]
        if isinstance(tail, AIMessage):
            return tail.content
        return str(tail)

    # Case 3: plain string / repr of AIMessage
    if isinstance(output, str):
        return output

    return None
