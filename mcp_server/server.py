# server.py
from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return (a + b)

if __name__ == "__main__":
    # mcp.run()
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
    # mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp")