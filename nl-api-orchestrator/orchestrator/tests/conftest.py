"""
Pytest fixtures for testing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


@pytest.fixture
def sample_capabilities():
    """Sample capability cards for testing."""
    return [
        {
            "name": "create_ticket",
            "description": "Create a support ticket",
            "endpoint": "POST https://api.example.com/tickets",
            "auth": "bearer",
            "risk": "medium",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 3},
                    "description": {"type": "string", "minLength": 10},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
                },
                "required": ["title", "description", "priority"]
            }
        }
    ]


@pytest.fixture
def mock_embed_server():
    """Mock embed server responses."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Mock embed response
        embed_response = AsyncMock()
        embed_response.json.return_value = {"vector": [0.1] * 384}
        embed_response.raise_for_status = MagicMock()

        # Mock search response
        search_response = AsyncMock()
        search_response.json.return_value = {
            "ids": ["create_ticket"],
            "scores": [0.95]
        }
        search_response.raise_for_status = MagicMock()

        mock_instance.post.side_effect = [embed_response, search_response]

        yield mock_client


@pytest.fixture
def mock_llm():
    """Mock LLM responses."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock completion response
        mock_response = AsyncMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "decision": "USE_TOOL",
                        "tool_name": "create_ticket",
                        "payload": {
                            "title": "Payment failure",
                            "description": "Gateway errors for user payment processing",
                            "priority": "urgent"
                        },
                        "notes": "Created ticket for payment issue"
                    })
                )
            )
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_mcp_client():
    """Mock MCP API client."""
    with patch('src.mcp_client.MCPClient') as mock_class:
        mock_instance = AsyncMock()
        mock_instance.invoke_tool.return_value = {
            "status": "ok",
            "ticket_id": "TKT-12345"
        }
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_opa_client():
    """Mock OPA policy client."""
    with patch('src.opa_client.OPAClient') as mock_class:
        mock_instance = AsyncMock()
        mock_instance.check_policy.return_value = {
            "allow": True,
            "reason": ""
        }
        mock_class.return_value = mock_instance
        yield mock_instance

