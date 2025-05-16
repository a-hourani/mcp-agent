# chat_app.py
import streamlit as st
import requests, json
from typing import Dict, Any, List

st.set_page_config(page_title="Streaming Chat", page_icon="💬")
st.title("Streaming Chat Application")

BACKEND_URL = "http://agent-api:7000/query"
HEADERS = {"accept": "application/json",
           "Content-Type": "application/json"}

# ─── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    # Each item may contain:
    #   role: "user" | "assistant"
    #   content: str                (always)
    #   tool_calls:  List[str]      (assistant only, optional)
    #   tool_output: str            (assistant only, optional)
    st.session_state.messages: List[Dict[str, str]] = []

if "chat_id" not in st.session_state:
    st.session_state.chat_id: str | None = None

# ─── Sidebar reset ─────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄  Reset chat", key="reset"):
        st.session_state.clear()
        st.rerun()

# ─── Helper ────────────────────────────────────────────────────────────────────
def parse_chunk(raw: str) -> Dict[str, Any]:
    """
    Backend lines start with 'data: '. Strip it and parse JSON.
    """
    try:
        return json.loads(raw[6:])
    except Exception:
        return {}

def render_assistant_message(msg: Dict[str, Any]) -> None:
    """
    Re-render a full assistant message from history, including any
    tool_calls / tool_output stored with it.
    """
    with st.chat_message("assistant"):
        # tool calls
        if msg.get("tool_calls"):
            with st.expander("🛠 Tool calls", expanded=False):
                for line in msg["tool_calls"]:
                    st.markdown(line)
        # tool output
        if msg.get("tool_output"):
            with st.expander("🔧 Tool output", expanded=False):
                st.markdown(f"```\n{msg['tool_output']}\n```")
        # assistant text
        st.markdown(msg["content"])

# ─── Replay history ────────────────────────────────────────────────────────────
for m in st.session_state.messages:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:  # assistant
        render_assistant_message(m)

# ─── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Type a message…")

if prompt:
    # ––– 1. show user message & store it ––––––––––––––––––––––––––––––––––––
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # ––– 2. assistant live containers ––––––––––––––––––––––––––––––––––––––––
    with st.chat_message("assistant"):
        calls_expander  = st.expander("🛠 Tool calls",  expanded=False)
        output_expander = st.expander("🔧 Tool output", expanded=False)
        reply_ph        = st.empty()

    assistant_text  = ""       # grows as we stream
    tool_call_lines = []       # list of strings like "`add(a=1,b=2)`"
    tool_output_str = ""       # full tool output (string)

    # ––– 3. build request ––––––––––––––––––––––––––––––––––––––––––––––––––––
    payload = {"message": prompt}
    if st.session_state.chat_id:
        payload["chat_id"] = st.session_state.chat_id
    data = json.dumps(payload)

    # ––– 4. stream –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    try:
        with requests.post(
            BACKEND_URL, headers=HEADERS, data=data, stream=True, timeout=None
        ) as resp:
            resp.raise_for_status()

            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                event = parse_chunk(raw)
                if not event:
                    continue

                # Remember chat_id for next round
                if "chat_id" in event:
                    st.session_state.chat_id = event["chat_id"]

                # >> Tool calls announced when model finishes planning
                if event.get("type") == "on_chat_model_end":
                    try:
                        output  = json.loads(event["data"]["output"])
                        calls   = output["additional_kwargs"]["tool_calls"]
                        for c in calls:
                            fn   = c["function"]["name"]
                            args = c["function"]["arguments"]
                            line = f"* `{fn}({args})`"
                            tool_call_lines.append(line)
                            calls_expander.markdown(line)
                    except Exception:
                        pass
                    continue  # no tokens in this chunk

                # >> Tool output when tool runs
                if event.get("type") == "on_tool_end":
                    try:
                        tool_output_str = json.loads(event["data"]["output"])["content"]
                        output_expander.markdown(f"```\n{tool_output_str}\n```")
                    except Exception:
                        pass
                    continue

                # >> Normal token stream
                if "data" in event:
                    chunk_str = event["data"].get("chunk", "{}")
                    try:
                        chunk = json.loads(chunk_str)
                    except Exception:
                        chunk = {}
                    piece = chunk.get("content")
                    if piece:
                        assistant_text += piece
                        reply_ph.markdown(assistant_text)

    except requests.RequestException as e:
        reply_ph.markdown(f"**Error:** {e}")
        st.stop()

    # ––– 5. store assistant message with tool metadata –––––––––––––––––––––––
    st.session_state.messages.append(
        {
            "role":        "assistant",
            "content":     assistant_text,
            "tool_calls":  tool_call_lines,
            "tool_output": tool_output_str,
        }
    )
