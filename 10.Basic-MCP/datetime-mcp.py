from fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP(name="Datetime-MCP")

@mcp.tool()
def get_current_datetime() -> str:
    """현재 날짜와 시간을 반환합니다."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    mcp.run()