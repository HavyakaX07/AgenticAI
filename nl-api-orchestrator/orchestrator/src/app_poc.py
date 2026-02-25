"""
POC VERSION - Main FastAPI application for the NL → API Orchestrator.
Simplified version without OpenTelemetry and Prometheus for faster startup.

Handles natural language queries and orchestrates API execution through RAG, LLM, and policy checks.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .settings import settings
from .retriever import CapabilityRetriever
from .tool_router import ToolRouter
from .validators import validate_payload
from .normalizers import normalize_payload
from .mcp_client import MCPClient
from .opa_client import OPAClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NL → API Orchestrator (POC)",
    description="Natural language to API orchestration with RAG, LLM reasoning, and policy enforcement",
    version="1.0.0-POC"
)


# Request/Response Models
class OrchestrationRequest(BaseModel):
    """Request model for orchestration endpoint."""
    query: str = Field(..., description="Natural language query from user", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID for multi-turn conversations")
    confirmed: Optional[bool] = Field(False, description="User confirmation for high-risk operations")


class OrchestrationResponse(BaseModel):
    """Response model for orchestration endpoint."""
    decision: str = Field(..., description="Decision: USE_TOOL, ASK_USER, GENERAL_RESPONSE, or NONE")
    tool_used: Optional[str] = Field(None, description="Name of the tool that was used")
    tool_name: Optional[str] = Field(None, description="Name of the selected tool")
    request_payload: Optional[Dict[str, Any]] = Field(None, description="Payload sent to the tool")
    api_result: Optional[Dict[str, Any]] = Field(None, description="Result from API execution")
    message: str = Field(..., description="Human-friendly message")
    missing_fields: Optional[list] = Field(None, description="List of missing required fields")
    session_id: str = Field(..., description="Session ID for this interaction")
    confirm_fields: Optional[Dict[str, Any]] = Field(None, description="Fields requiring confirmation")


# Initialize components
retriever: Optional[CapabilityRetriever] = None
router: Optional[ToolRouter] = None
mcp_client: Optional[MCPClient] = None
opa_client: Optional[OPAClient] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global retriever, router, mcp_client, opa_client

    logger.info("=" * 80)
    logger.info("Starting NMS Credential Management Orchestrator (POC Mode)...")
    logger.info("=" * 80)
    logger.info(f"LLM Provider : {settings.llm_provider}")
    logger.info(f"Model        : {settings.model_name}")
    logger.info(f"Embed Server : {settings.embed_server_url}")
    logger.info(f"API Tools    : {settings.api_tools_url}")
    logger.info(f"OPA          : {settings.opa_url}")
    logger.info(f"Registry     : {settings.registry_path}")
    logger.info(f"NLP Metadata : {settings.nlp_metadata_path}")
    logger.info("=" * 80)

    try:
        # Initialize retriever (RAG component)
        logger.info("Initializing Capability Retriever...")
        retriever = CapabilityRetriever(
            registry_path=settings.registry_path,
            embed_server_url=settings.embed_server_url
        )
        await retriever.initialize()
        logger.info(f"✓ Loaded {len(retriever.capabilities)} capabilities")

        # Initialize router (LLM component)
        logger.info("Initializing Tool Router...")
        router = ToolRouter(
            openai_base_url=settings.openai_base_url,
            openai_api_key=settings.openai_api_key,
            model_name=settings.model_name
        )
        logger.info("✓ Tool Router initialized")

        # Initialize MCP client (Tool execution)
        logger.info("Initializing MCP Client...")
        mcp_client = MCPClient(api_tools_url=settings.api_tools_url)
        logger.info("✓ MCP Client initialized")

        # Initialize OPA client (Policy enforcement)
        logger.info("Initializing OPA Client...")
        opa_client = OPAClient(opa_url=settings.opa_url)
        logger.info("✓ OPA Client initialized")

        logger.info("=" * 80)
        logger.info("✓ All components initialized successfully")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "POC",
        "services": {}
    }

    # Check LLM
    try:
        if router:
            await router.check_health()
            health_status["services"]["llm"] = "healthy"
        else:
            health_status["services"]["llm"] = "not_initialized"
    except Exception as e:
        health_status["services"]["llm"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check embed server
    try:
        if retriever:
            await retriever.check_health()
            health_status["services"]["embed"] = "healthy"
        else:
            health_status["services"]["embed"] = "not_initialized"
    except Exception as e:
        health_status["services"]["embed"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check API tools
    try:
        if mcp_client:
            await mcp_client.check_health()
            health_status["services"]["api_tools"] = "healthy"
        else:
            health_status["services"]["api_tools"] = "not_initialized"
    except Exception as e:
        health_status["services"]["api_tools"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check OPA
    try:
        if opa_client:
            await opa_client.check_health()
            health_status["services"]["policy"] = "healthy"
        else:
            health_status["services"]["policy"] = "not_initialized"
    except Exception as e:
        health_status["services"]["policy"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


def _build_nms_message(tool_name: str, payload: dict, api_result: dict, notes: str) -> str:
    """
    Build a human-friendly response message using NMS response_templates
    from credential_api_nlp_metadata.json.
    """
    status = api_result.get("status", "success")
    error  = api_result.get("error", api_result.get("message", ""))

    if status in ("error", "failed"):
        return f"Operation failed: {error}" if error else f"{tool_name} failed."

    if tool_name == "copy_device_credentials":
        src   = payload.get("source", "source device")
        dests = payload.get("destinations", [])
        count = api_result.get("credentials_copied", len(dests))
        dest_str = ", ".join(dests) if isinstance(dests, list) else str(dests)
        return f"Successfully copied credentials from {src} to {count} device(s): {dest_str}"

    if tool_name == "get_device_detail_credentials":
        dev = payload.get("deviceId", "device")
        snmp_status = "configured" if api_result.get("snmpRead") else "not configured"
        cli_status  = "configured" if api_result.get("cli")     else "not configured"
        return f"Retrieved credentials for device {dev}. SNMP: {snmp_status}, CLI: {cli_status}"

    if tool_name in ("set_device_credentials", "set_bulk_device_credentials"):
        dev_ids = payload.get("deviceId", payload.get("deviceIds", []))
        count   = len(dev_ids) if isinstance(dev_ids, list) else 1
        return f"Successfully updated credentials for {count} device(s)"

    if tool_name == "delete_device_credentials":
        dev_ids = payload.get("deviceIds", [])
        count   = len(dev_ids) if isinstance(dev_ids, list) else 1
        return f"Successfully deleted credentials for {count} device(s)"

    if tool_name == "trust_device_credentials":
        dev_ids = payload.get("deviceIds", [])
        return f"Trusted {len(dev_ids) if isinstance(dev_ids, list) else 1} device(s)"

    if tool_name == "untrust_device_credentials":
        dev_ids = payload.get("deviceIds", [])
        return f"Revoked trust for {len(dev_ids) if isinstance(dev_ids, list) else 1} device(s)"

    if tool_name == "get_all_device_credentials":
        count = api_result.get("total", api_result.get("count", "all"))
        return f"Retrieved {count} device credential records"

    if tool_name == "get_https_certificate":
        dev = payload.get("deviceId", "device")
        return f"Retrieved HTTPS certificate for device {dev}"

    if tool_name == "get_https_port":
        dev  = payload.get("deviceId", "device")
        port = api_result.get("httpsPort", "")
        return f"HTTPS port for {dev} is {port}" if port else f"Retrieved HTTPS port for {dev}"

    if tool_name == "check_role_rights_credentials":
        rights = api_result.get("rights", api_result.get("role", ""))
        return f"Your access rights: {rights}" if rights else "Retrieved your permission details"

    if tool_name == "view_decrypted_password":
        return "Decrypted password retrieved successfully"

    # Fallback
    return notes or f"Successfully executed {tool_name}."


@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate(request: OrchestrationRequest):
    """
    Main orchestration endpoint.

    Flow:
    1. RAG: Retrieve candidate capabilities based on semantic similarity
    2. LLM: Select best tool and extract parameters from natural language
    3. Validate: JSON schema validation of extracted parameters
    4. Normalize: Apply normalizations (e.g., lowercase, trim)
    5. Policy: Check OPA policies for authorization
    6. Execute: Call MCP API tools to perform the action
    7. Summarize: Return user-friendly response
    """
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"[{session_id}] ========================================")
    logger.info(f"[{session_id}] New orchestration request")
    logger.info(f"[{session_id}] Query: {request.query}")
    logger.info(f"[{session_id}] ========================================")

    try:
        # Step 1: RAG - Retrieve candidate capabilities
        logger.info(f"[{session_id}] Step 1: Retrieving capabilities via RAG...")
        candidates = await retriever.retrieve(request.query, top_k=1)
        logger.info(f"[{session_id}] → Found {len(candidates)} candidate capabilities")
        for i, candidate in enumerate(candidates, 1):
            logger.info(f"[{session_id}]   {i}. {candidate['name']}: {candidate['description'][:-1]}...")

        # Step 2: LLM - Select tool and fill payload (or handle general conversation)
        # Even if no candidates found, LLM can detect general conversational queries
        logger.info(f"[{session_id}] Step 2: LLM reasoning for tool selection...")
        llm_response = await router.route(request.query, candidates)
        decision = llm_response.get("decision", "NONE")
        tool_name = llm_response.get("tool_name")
        payload = llm_response.get("payload", {})
        missing_fields = llm_response.get("missing_fields", [])
        notes = llm_response.get("notes", "")

        logger.info(f"[{session_id}] → LLM Decision: {decision}")
        logger.info(f"[{session_id}] → Tool Name: {tool_name}")
        logger.info(f"[{session_id}] → Payload: {payload}")

        # Handle GENERAL_RESPONSE decision (greetings, thanks, general conversation)
        if decision == "GENERAL_RESPONSE":
            response_text = llm_response.get("response", "Hello! How can I help you with network device management today?")
            logger.info(f"[{session_id}] → General conversational response")
            return OrchestrationResponse(
                decision="GENERAL_RESPONSE",
                message=response_text,
                session_id=session_id
            )

        # Handle ASK_USER decision
        if decision == "ASK_USER" or missing_fields:
            logger.info(f"[{session_id}] → Need more information from user")
            message = f"I need more information"
            if missing_fields:
                fields_str = ", ".join(missing_fields)
                message += f" to {tool_name or 'proceed'}. Please provide: {fields_str}"
            if notes:
                message += f". {notes}"

            return OrchestrationResponse(
                decision="ASK_USER",
                tool_name=tool_name,
                missing_fields=missing_fields,
                message=message,
                session_id=session_id
            )

        # Handle NONE decision
        if decision == "NONE" or not tool_name:
            logger.info(f"[{session_id}] → No appropriate tool found")
            message = notes or "I couldn't find an appropriate tool for this request."
            return OrchestrationResponse(
                decision="NONE",
                message=message,
                session_id=session_id
            )

        # Get the selected capability
        capability = next((c for c in candidates if c["name"] == tool_name), None)
        if not capability:
            raise HTTPException(
                status_code=500,
                detail=f"LLM selected unknown tool: {tool_name}"
            )

        # Step 3: Validate payload
        logger.info(f"[{session_id}] Step 3: Validating payload...")
        is_valid, validation_error = validate_payload(
            payload,
            capability["input_schema"],
            tool_name=tool_name          # enables NMS conditional SNMP checks
        )

        if not is_valid:
            logger.warning(f"[{session_id}] → Validation failed: {validation_error}")
            return OrchestrationResponse(
                decision="ASK_USER",
                tool_name=tool_name,
                message=f"Invalid payload: {validation_error}",
                session_id=session_id
            )
        logger.info(f"[{session_id}] → Validation passed")

        # Step 4: Normalize payload
        logger.info(f"[{session_id}] Step 4: Normalizing payload...")
        payload = normalize_payload(payload, capability)
        logger.info(f"[{session_id}] → Normalized payload: {payload}")

        # Step 5: Policy check
        logger.info(f"[{session_id}] Step 5: Checking OPA policy...")
        risk_level = capability.get("risk", "medium")
        policy_input = {
            "payload": payload,
            "tool": tool_name,
            "risk": risk_level,
            "confirmed": request.confirmed,
            "user": "default_user"
        }

        policy_result = await opa_client.check_policy(policy_input)
        logger.info(f"[{session_id}] → Policy result: {policy_result}")

        if not policy_result.get("allow", False):
            reason = policy_result.get("reason", "Policy check failed")
            logger.warning(f"[{session_id}] → Policy denied: {reason}")

            # high and critical operations both require confirmation
            if risk_level in ("high", "critical") and not request.confirmed:
                return OrchestrationResponse(
                    decision="ASK_USER",
                    tool_name=tool_name,
                    request_payload=payload,
                    message=f"This is a {risk_level}-risk operation ({tool_name}). {reason}. Please confirm by re-sending with confirmed=true.",
                    confirm_fields=payload,
                    session_id=session_id
                )

            return OrchestrationResponse(
                decision="ASK_USER",
                tool_name=tool_name,
                message=f"Policy check failed: {reason}",
                session_id=session_id
            )

        # Step 6: Execute via MCP API tools
        logger.info(f"[{session_id}] Step 6: Executing tool via MCP...")
        api_result = await mcp_client.invoke_tool(tool_name, payload)
        logger.info(f"[{session_id}] → Tool execution result: {api_result.get('status')}")
        logger.info(f"[{session_id}] → API result: {api_result}")

        # Step 7: Generate NMS-aware user-friendly message
        message = _build_nms_message(tool_name, payload, api_result, notes)

        logger.info(f"[{session_id}] ========================================")
        logger.info(f"[{session_id}] ✓ Orchestration completed successfully")
        logger.info(f"[{session_id}] ========================================")

        return OrchestrationResponse(
            decision="USE_TOOL",
            tool_used=tool_name,
            request_payload=payload,
            api_result=api_result,
            message=message,
            session_id=session_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{session_id}] Orchestration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Orchestration failed: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

