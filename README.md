## Chatbot Application built with:
 - Streamlit UI 
 - FastApi + SQLite
 - langchain agent 
 - MCP tool

## Chatbot UI
![Chatbot UI](media/chatbot_ui.jpg)

## How To Deploy
 - docker build -t mcp-server mcp_server 
 - docker build -t agent-api agent_api 
 - docker build -t agent-ui agent_ui
 - docker compose up 

