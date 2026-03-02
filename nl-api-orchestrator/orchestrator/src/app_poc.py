"""
POC VERSION - Main FastAPI application for the NL → API Orchestrator.
Simplified version without OpenTelemetry and Prometheus for faster startup.

Handles natural language queries and orchestrates API execution through RAG, LLM, and policy checks.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

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
from .device_resolver import DeviceResolver, ResolutionMode

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
    # Device resolution — populated when a reference matched multiple devices
    ambiguous_devices: Optional[Dict[str, Any]] = Field(
        None,
        description="Map of ambiguous device reference → list of candidate devices with device_id, displayName, ip, location"
    )
    # Device resolution — populated when a reference was fully resolved (for traceability)
    resolved_devices: Optional[Dict[str, str]] = Field(
        None,
        description="Map of original reference → resolved device_id (informational)"
    )


# Initialize components
retriever: Optional[CapabilityRetriever] = None
router: Optional[ToolRouter] = None
mcp_client: Optional[MCPClient] = None
opa_client: Optional[OPAClient] = None
device_resolver: Optional[DeviceResolver] = None


@app.on_event("shutdown")
async def shutdown_event():
    """Close DB connections cleanly on shutdown."""
    if device_resolver:
        await device_resolver.close()
        logger.info("Device Resolver connection closed.")


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup."""
    # Declare global variables so we update them instead of creating local ones
    global retriever, router, mcp_client, opa_client, device_resolver

    logger.info("=" * 80)
    logger.info("Starting NMS Credential Management Orchestrator (POC Mode)...")
    logger.info("=" * 80)
    logger.info(f"LLM Provider : {settings.llm_provider} (host-installed, not a container)")
    logger.info(f"Ollama URL   : {settings.openai_base_url}  ← must be running on host")
    logger.info(f"Model        : {settings.model_name}")
    logger.info(f"Embed Server : {settings.embed_server_url}")
    logger.info(f"API Tools    : {settings.api_tools_url}")
    logger.info(f"OPA          : {settings.opa_url}")
    logger.info(f"Registry     : {settings.registry_path}")
    logger.info(f"NLP Metadata : {settings.nlp_metadata_path}")
    logger.info("=" * 80)
    logger.info("PRE-REQUISITE: Ollama must be installed on the host and serving.")
    logger.info("  1. Install : https://ollama.com")
    logger.info("  2. Start   : ollama serve")
    logger.info(f"  3. Pull    : ollama pull {settings.model_name}")
    logger.info("=" * 80)

    try:
        # Initialize retriever (RAG component)
        logger.info("Initializing Capability Retriever...")
        retriever = CapabilityRetriever(
            registry_path=settings.registry_path,
            embed_server_url=settings.embed_server_url
        )
        logger.info(f"CapabilityRetriever is {retriever}")
        await retriever.initialize()
        logger.info(f"✓ Loaded {len(retriever.capabilities)} capabilities")

        # Initialize router (LLM component)
        logger.info("Initializing Tool Router...")
        router = ToolRouter(
            openai_base_url=settings.openai_base_url,
            openai_api_key=settings.openai_api_key,
            model_name=settings.model_name
        )
        logger.info(f"router is {router}")
        logger.info("✓ Tool Router initialized")

        # Initialize MCP client (Tool execution)
        logger.info("Initializing MCP Client...")
        mcp_client = MCPClient(api_tools_url=settings.api_tools_url)
        logger.info("✓ MCP Client initialized")
        logger.info(f"mcp_client is {mcp_client}")

        # Initialize OPA client (Policy enforcement)
        logger.info("Initializing OPA Client...")
        opa_client = OPAClient(opa_url=settings.opa_url)
        logger.info(f"✓ OPA Client initialized {opa_client}")

        # Initialize Device Resolver (brand/IP/type → device_id)
        logger.info("Initializing Device Resolver...")
        device_resolver = DeviceResolver(
            db_backend   = settings.db_backend,
            db_url       = settings.db_url,
            sqlite_path  = settings.sqlite_path,
            nms_base_url = settings.nms_device_api_url or None,
            token        = settings.api_token,
            use_mock     = settings.device_resolver_mock,
        )
        await device_resolver.initialize()   # opens DB pool (no-op for mock)
        logger.info(f"✓ Device Resolver initialized (backend={device_resolver.db_backend})")

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
    # Log all the component hash code to check it is none
    logger.info(f"Health Check - Component Status:")
    logger.info(f"  Router: {router} (id={id(router)})")
    logger.info(f"  Retriever: {retriever} (id={id(retriever)})")
    logger.info(f"  MCP Client: {mcp_client} (id={id(mcp_client)})")
    logger.info(f"  Resolver: {device_resolver} (id={id(device_resolver)})")
    logger.info(f"  OPA Client: {opa_client} (id={id(opa_client)})")
    logger.info(f"  Settings: {settings} (id={id(settings)})")


    # Check LLM
    try:
        if router:
            await router.check_health()
            logger.info("LLM is healthy")
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
            logger.info("Embed server is healty")
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
            logger.info("MCP client is healthy")
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
            logger.info("OPA is healthy")
            health_status["services"]["policy"] = "healthy"
        else:
            health_status["services"]["policy"] = "not_initialized"
    except Exception as e:
        health_status["services"]["policy"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Device Resolver & Cache
    try:
        if device_resolver:
            cache_stats = device_resolver.get_cache_stats()
            health_status["services"]["device_resolver"] = {
                "status": "healthy",
                "backend": cache_stats["backend"],
                "cache": {
                    "total_devices": cache_stats["total_devices"],
                    "age_seconds": cache_stats["cache_age_seconds"],
                    "last_refresh": cache_stats["last_refresh"],
                    "refresh_interval": cache_stats["refresh_interval_seconds"]
                }
            }
            logger.info(f"Device Resolver: {cache_stats['total_devices']} devices cached (age: {cache_stats['cache_age_seconds']}s)")
        else:
            health_status["services"]["device_resolver"] = "not_initialized"
    except Exception as e:
        health_status["services"]["device_resolver"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


async def _resolve_device_references(
    tool_name: str,
    payload: dict,
    session_id: str,
    mode: ResolutionMode = ResolutionMode.NORMAL,
) -> tuple:
    """
    Step 2.5 - Resolve human-readable device references to actual NMS device_ids.

    Fields examined:
      Scalar : source, deviceId
      List   : destinations, deviceIds, deleteDevIds

    Resolution behaviour per mode:
      NORMAL   single match → replace silently
               multiple matches → ASK_USER with disambiguation list
               no match → ASK_USER asking for correct device
      ALL      multiple matches → expand ALL device_ids automatically (no ask)
               e.g. "trust all scalance" → [SCALANCE-X200-001, SCALANCE-X200-002, SCALANCE-XC200-001]
      ANY_ONE  multiple matches → pick FIRST device_id automatically (no ask)
               e.g. "copy from any ruggedcom" → RUGGEDCOM-RS900-001

    Returns:
        (resolved_payload, ask_user_dict_or_None, resolved_map)
        ask_user_dict is None when resolution succeeded without needing user input.
        resolved_map = { original_ref → resolved_device_id } for traceability.
    """
    if not device_resolver:
        return payload, None, {}

    SCALAR_FIELDS = ["source", "deviceId"]
    LIST_FIELDS   = ["destinations", "deviceIds", "deleteDevIds"]

    updated      = dict(payload)
    ambiguous_map = {}  # ref -> [candidates]  (only populated in NORMAL mode)
    unresolved    = []
    resolved_map  = {}  # original_ref -> resolved_device_id

    def _apply(field: str, ref: str, matches: List[Dict[str, Any]]) -> Optional[List[str]]:
        """
        Decide what to do with matches for a single reference.
        Returns list of resolved device_ids, or None if unresolved.
        Also populates ambiguous_map when mode=NORMAL and multiple matches exist.
        """
        if not matches:
            return None  # unresolved

        if len(matches) == 1:
            return [matches[0]["device_id"]]

        # Multiple matches
        if mode == ResolutionMode.ALL:
            ids = [m["device_id"] for m in matches]
            logger.info(f"[{session_id}] ALL mode: '{ref}' → expanded to {ids}")
            return ids

        if mode == ResolutionMode.ANY_ONE:
            chosen = matches[0]["device_id"]
            logger.info(f"[{session_id}] ANY_ONE mode: '{ref}' → picked '{chosen}' from {len(matches)} matches")
            return [chosen]

        # NORMAL mode — flag as ambiguous, caller will ask user
        ambiguous_map[ref] = matches
        return None  # signals ambiguous

    # ── Scalar fields ─────────────────────────────────────────────────────────
    for field in SCALAR_FIELDS:
        ref = updated.get(field)
        if not ref or not isinstance(ref, str):
            continue
        matches = await device_resolver.resolve(ref, mode)
        resolved_ids = _apply(field, ref, matches)

        if resolved_ids is None and ref not in ambiguous_map:
            unresolved.append(ref)
        elif resolved_ids:
            if mode == ResolutionMode.ALL and len(resolved_ids) > 1:
                # Scalar field can't hold multiple — promote to list field if possible
                # For "source" there's no natural list equivalent; just use first and warn
                # For "deviceId" we could promote to deviceIds — handled below
                if field == "deviceId":
                    updated.pop("deviceId", None)
                    updated["deviceIds"] = resolved_ids
                    for rid in resolved_ids:
                        resolved_map[ref] = resolved_ids  # map to list
                    logger.info(f"[{session_id}] Promoted deviceId → deviceIds: {resolved_ids}")
                else:
                    # source field — use first device and log a note
                    updated[field] = resolved_ids[0]
                    resolved_map[ref] = resolved_ids[0]
                    logger.warning(
                        f"[{session_id}] ALL mode on scalar field '{field}': "
                        f"using first match '{resolved_ids[0]}' (consider using a list field)"
                    )
            else:
                # Single resolved id (or ANY_ONE first pick)
                updated[field] = resolved_ids[0]
                if ref != resolved_ids[0]:
                    resolved_map[ref] = resolved_ids[0]
                    logger.info(f"[{session_id}] Resolved '{ref}' → '{resolved_ids[0]}' (field={field})")

    # ── List fields ───────────────────────────────────────────────────────────
    for field in LIST_FIELDS:
        refs = updated.get(field)
        if not refs or not isinstance(refs, list):
            continue
        resolved_list = []
        for ref in refs:
            matches    = await device_resolver.resolve(ref, mode)
            resolved_ids = _apply(field, ref, matches)

            if resolved_ids is None and ref not in ambiguous_map:
                unresolved.append(ref)
                resolved_list.append(ref)       # keep original so validation catches it
            elif resolved_ids:
                resolved_list.extend(resolved_ids)  # ALL → multiple IDs flattened into list
                if ref != resolved_ids[0]:
                    resolved_map[ref] = resolved_ids if len(resolved_ids) > 1 else resolved_ids[0]
                    logger.info(f"[{session_id}] Resolved '{ref}' → {resolved_ids} (field={field})")
            else:
                resolved_list.append(ref)       # ambiguous — keep original

        updated[field] = resolved_list

    # ── Ambiguous (NORMAL mode only) ──────────────────────────────────────────
    if ambiguous_map:
        choices_msg = []
        for ref, candidates in ambiguous_map.items():
            options = ", ".join(
                f"{c['device_id']} ({c.get('display_name', c.get('displayName', ''))}"
                f" IP={c['ip']} Loc={c.get('location', '')})"
                for c in candidates
            )
            choices_msg.append(f"'{ref}' matched {len(candidates)} devices: [{options}]")

        message = (
            "I found multiple devices matching your reference(s). "
            "Please specify the exact device ID, or rephrase using 'all' or 'any':\n"
            + "\n".join(choices_msg)
        )
        logger.info(f"[{session_id}] Ambiguous references (NORMAL mode): {list(ambiguous_map.keys())}")
        return updated, {
            "decision": "ASK_USER",
            "tool_name": tool_name,
            "message": message,
            "missing_fields": [f"exact device_id for: {ref}" for ref in ambiguous_map],
            "ambiguous_devices": {
                ref: [
                    {
                        "device_id":    c["device_id"],
                        "display_name": c.get("display_name", c.get("displayName", "")),
                        "ip":           c["ip"],
                        "location":     c.get("location", ""),
                    }
                    for c in candidates
                ]
                for ref, candidates in ambiguous_map.items()
            },
        }, resolved_map

    # ── Unresolved ────────────────────────────────────────────────────────────
    if unresolved:
        message = (
            f"I could not find the following device(s): {', '.join(unresolved)}. "
            "Please provide a valid device ID, IP address, or exact device name."
        )
        logger.warning(f"[{session_id}] Unresolved device references: {unresolved}")
        return updated, {
            "decision": "ASK_USER",
            "tool_name": tool_name,
            "message": message,
            "missing_fields": [f"valid device ID for: {ref}" for ref in unresolved],
        }, resolved_map

    return updated, None, resolved_map


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

        # Step 2.5: Device Resolution — translate brand/IP/type → real device_ids
        # Detect ALL / ANY_ONE intent from the original query BEFORE LLM extraction
        resolution_mode = device_resolver.detect_resolution_mode(request.query) if device_resolver else ResolutionMode.NORMAL
        logger.info(f"[{session_id}] Step 2.5: Resolving device references (mode={resolution_mode.value})...")
        payload, ask_response, resolved_map = await _resolve_device_references(
            tool_name, payload, session_id, resolution_mode
        )
        if ask_response:
            # Ambiguous (multiple matches in NORMAL mode) or unresolved → ask user
            return OrchestrationResponse(
                decision=ask_response["decision"],
                tool_name=ask_response["tool_name"],
                missing_fields=ask_response.get("missing_fields"),
                message=ask_response["message"],
                confirm_fields=ask_response.get("ambiguous_devices"),
                ambiguous_devices=ask_response.get("ambiguous_devices"),
                session_id=session_id,
            )
        if resolved_map:
            logger.info(f"[{session_id}] → Device resolution map: {resolved_map}")
        logger.info(f"[{session_id}] → Resolved payload: {payload}")

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
            resolved_devices=resolved_map if resolved_map else None,
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

