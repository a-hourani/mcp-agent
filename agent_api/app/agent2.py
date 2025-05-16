# app/agent.py
from contextlib import asynccontextmanager
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from uuid import UUID

from langchain.schema import HumanMessage, AIMessage


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


async def run_agent_stream(chat_id: UUID, user_msg: str):
    """
    Yields every event emitted by the agent as a dict.
    Events include:
      - thought / action / observation (tool call + result)
      - final answer
    """
    from app.db import save_message, fetch_history                       # late import avoids circulars
    # Persist the user message
    # await save_message(chat_id, "user", user_msg)
    past = await fetch_history(chat_id, limit=20)

    history_msgs = []
    for role, content in past:
        if role == "user":
            history_msgs.append(HumanMessage(content=content))
        else:                       # "assistant"
            history_msgs.append(AIMessage(content=content))

    # 3️⃣  add the fresh user message
    history_msgs.append(HumanMessage(content=user_msg))

    # 4️⃣  save it so the next call can retrieve it
    await save_message(chat_id, "user", user_msg)

    # 5️⃣  stream the agent
    # async with agent_ctx() as agent:
    #     async for event in agent.astream_events({"messages": history_msgs}):

    # # LangGraph/LC expects a list of dicts like {"role": "user", "content": "..."}
    # history_msgs = [{"role": role, "content": content} for role, content in past]

    # # Append the new user message we just received
    # prompt_messages = history_msgs + [{"role": "user", "content": user_msg}]

    # # Persist the fresh user turn
    # await save_message(chat_id, "user", user_msg)

    async with agent_ctx() as agent:
        # LangGraph supports rich streaming:
        # async for event in agent.astream_events({"messages": history_msgs}):
        print(history_msgs)
        async for event in agent.astream_events({"messages": [HumanMessage('hi'),AIMessage('Hello!'),HumanMessage('what was my first message to you, and what was your response?')]}):
            kind = event["event"]
            content = event["data"]

            # Persist assistant steps (optional, only 'final' below is required)
            if kind == "final":
                await save_message(chat_id, "assistant", content[-1].content)

            yield {
                "type": kind,           # thought / tool_call / tool_result / final
                "data": content,
                "chat_id": str(chat_id)
            }
