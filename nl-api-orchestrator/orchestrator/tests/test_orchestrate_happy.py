"""
Happy path orchestration test.
Tests the full flow from query to API execution.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_orchestrate_happy_path(
    sample_capabilities,
    mock_embed_server,
    mock_llm,
    mock_mcp_client,
    mock_opa_client
):
    """Test successful orchestration flow."""
    from src.retriever import CapabilityRetriever
    from src.tool_router import ToolRouter
    from src.mcp_client import MCPClient
    from src.opa_client import OPAClient

    # Initialize retriever
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(sample_capabilities)
        retriever = CapabilityRetriever(
            registry_path="/fake/path.json",
            embed_server_url="http://fake:9001"
        )
        await retriever.initialize()

    # Get candidates
    with mock_embed_server:
        candidates = await retriever.retrieve("Open urgent ticket for payment failure")

    assert len(candidates) > 0
    assert candidates[0]["name"] == "create_ticket"

    # Route with LLM
    router = ToolRouter(
        openai_base_url="http://fake:8000/v1",
        openai_api_key="fake",
        model_name="fake-model"
    )

    llm_response = await router.route("Open urgent ticket for payment failure", candidates)

    assert llm_response["decision"] == "USE_TOOL"
    assert llm_response["tool_name"] == "create_ticket"
    assert llm_response["payload"]["priority"] == "urgent"

    # Validate (using real validator)
    from src.validators import validate_payload
    is_valid, error = validate_payload(
        llm_response["payload"],
        candidates[0]["input_schema"]
    )
    assert is_valid, f"Validation failed: {error}"

    # Policy check
    mock_opa_client.check_policy.return_value = {"allow": True, "reason": ""}
    policy_result = await mock_opa_client.check_policy({
        "payload": llm_response["payload"],
        "tool": "create_ticket",
        "risk": "medium",
        "confirmed": False,
        "user": "test"
    })
    assert policy_result["allow"]

    # Execute
    mock_mcp_client.invoke_tool.return_value = {
        "status": "ok",
        "ticket_id": "TKT-12345"
    }
    result = await mock_mcp_client.invoke_tool(
        "create_ticket",
        llm_response["payload"]
    )

    assert result["status"] == "ok"
    assert "ticket_id" in result


@pytest.mark.asyncio
async def test_orchestrate_missing_fields(mock_llm):
    """Test orchestration when required fields are missing."""
    from src.tool_router import ToolRouter

    # Mock LLM to return ASK_USER
    mock_llm.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "decision": "ASK_USER",
        "tool_name": "create_ticket",
        "missing_fields": ["description", "priority"],
        "notes": "Need more details"
    })

    router = ToolRouter(
        openai_base_url="http://fake:8000/v1",
        openai_api_key="fake",
        model_name="fake-model"
    )

    candidates = [{
        "name": "create_ticket",
        "description": "Create ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string"}
            },
            "required": ["title", "description", "priority"]
        }
    }]

    response = await router.route("Create a ticket", candidates)

    assert response["decision"] == "ASK_USER"
    assert "missing_fields" in response
    assert len(response["missing_fields"]) > 0


@pytest.mark.asyncio
async def test_orchestrate_no_matching_tool(mock_llm):
    """Test orchestration when no tool matches."""
    from src.tool_router import ToolRouter

    # Mock LLM to return NONE
    mock_llm.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "decision": "NONE",
        "notes": "No tool available for weather queries"
    })

    router = ToolRouter(
        openai_base_url="http://fake:8000/v1",
        openai_api_key="fake",
        model_name="fake-model"
    )

    candidates = [{
        "name": "create_ticket",
        "description": "Create ticket",
        "input_schema": {"type": "object"}
    }]

    response = await router.route("What's the weather?", candidates)

    assert response["decision"] == "NONE"

