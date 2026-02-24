"""
MCP API Tools Server.
Exposes business API tools as HTTP endpoints with allowlist enforcement.
"""
import logging
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .tools import TOOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP API Tools Server",
    description="Executes API tools with allowlist enforcement",
    version="1.0.0"
)

# Load configuration
API_TOKEN = os.getenv("API_TOKEN", "demo-token")
ALLOWLIST_PREFIXES = os.getenv("ALLOWLIST_PREFIXES", "https://api.example.com/").split(",")
ALLOWLIST_PREFIXES = [p.strip() for p in ALLOWLIST_PREFIXES if p.strip()]

logger.info(f"Initialized with allowlist: {ALLOWLIST_PREFIXES}")


class ToolListRequest(BaseModel):
    """Request for listing tools."""
    pass


class ToolInvokeRequest(BaseModel):
    """Request for invoking a tool."""
    tool: str
    args: Dict[str, Any]


class ToolListResponse(BaseModel):
    """Response for tool listing."""
    tools: Dict[str, Dict[str, Any]]


class ToolInvokeResponse(BaseModel):
    """Response for tool invocation."""
    status: str
    result: Dict[str, Any] = {}
    error: str = ""


def is_allowed(url: str) -> bool:
    """
    Check if URL is in allowlist.

    Args:
        url: URL to check

    Returns:
        True if allowed, False otherwise
    """
    return any(url.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "tools_count": len(TOOLS)}


@app.post("/tools/list", response_model=ToolListResponse)
async def list_tools(request: ToolListRequest):
    """
    List available tools with their schemas.

    Returns:
        Dictionary of tool names to schemas
    """
    tool_schemas = {}

    for tool_name, tool_func in TOOLS.items():
        # Get docstring as description
        description = tool_func.__doc__ or f"Execute {tool_name}"
        tool_schemas[tool_name] = {
            "description": description.strip(),
            "function": tool_name
        }

    logger.info(f"Listed {len(tool_schemas)} tools")
    return ToolListResponse(tools=tool_schemas)


@app.post("/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(request: ToolInvokeRequest):
    """
    Invoke a tool with given arguments.

    Args:
        request: Tool name and arguments

    Returns:
        Result from tool execution
    """
    tool_name = request.tool
    args = request.args

    logger.info(f"Invoking tool: {tool_name} with args: {args}")

    # Check if tool exists
    if tool_name not in TOOLS:
        logger.error(f"Unknown tool: {tool_name}")
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    try:
        # Get tool function
        tool_func = TOOLS[tool_name]

        # Execute tool (pass allowlist and token)
        result = await tool_func(args, ALLOWLIST_PREFIXES, API_TOKEN)

        logger.info(f"Tool {tool_name} executed successfully")
        return ToolInvokeResponse(
            status="ok",
            result=result
        )

    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return ToolInvokeResponse(
            status="error",
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)

