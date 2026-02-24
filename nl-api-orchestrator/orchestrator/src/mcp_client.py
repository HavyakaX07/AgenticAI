"""
MCP API Tools client.
Communicates with the MCP API server to list and invoke tools.
"""
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for MCP API Tools server."""

    def __init__(self, api_tools_url: str):
        """
        Initialize MCP client.

        Args:
            api_tools_url: Base URL of MCP API tools server
        """
        self.api_tools_url = api_tools_url
        logger.info(f"Initialized MCPClient with URL: {api_tools_url}")

    async def check_health(self):
        """Check if API tools server is healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_tools_url}/health",
                timeout=5.0
            )
            response.raise_for_status()

    async def list_tools(self) -> Dict[str, Any]:
        """
        List available tools from MCP server.

        Returns:
            Dict with tools and their schemas
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_tools_url}/tools/list",
                json={},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def invoke_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a tool via MCP server.

        Args:
            tool_name: Name of the tool to invoke
            args: Arguments for the tool

        Returns:
            Result from tool execution
        """
        logger.info(f"Invoking tool: {tool_name} with args: {args}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_tools_url}/tools/invoke",
                    json={
                        "tool": tool_name,
                        "args": args
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Tool {tool_name} executed successfully")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Tool invocation failed with status {e.response.status_code}: {e.response.text}")
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Tool invocation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

