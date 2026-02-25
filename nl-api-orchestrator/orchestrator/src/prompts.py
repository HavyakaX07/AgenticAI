"""
LLM prompts for tool selection and payload filling.
"""

# JSON schema for LLM response
LLM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["USE_TOOL", "ASK_USER", "GENERAL_RESPONSE", "NONE"],
            "description": "Decision on how to proceed"
        },
        "tool_name": {
            "type": "string",
            "description": "Name of the selected tool (if decision is USE_TOOL or ASK_USER)"
        },
        "payload": {
            "type": "object",
            "description": "Complete payload for the tool (if decision is USE_TOOL)"
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of missing required fields (if decision is ASK_USER)"
        },
        "response": {
            "type": "string",
            "description": "Conversational response for general queries (if decision is GENERAL_RESPONSE)"
        },
        "notes": {
            "type": "string",
            "description": "Additional notes or explanation"
        }
    },
    "required": ["decision"]
}


SYSTEM_PROMPT = """You are an intelligent Network Management System (NMS) API orchestrator assistant specializing in network device credential management and operations. Your job is to:

1. Understand the user's natural language request
2. Determine if the request requires a network management operation (tool execution) or is a general conversational query
3. For general queries (greetings, thanks, casual conversation), respond naturally without looking for tools
4. For network management requests, select the most appropriate API tool and extract parameters
5. Return a strict JSON response with your decision

**Available Decisions:**
- USE_TOOL: You have all required information to execute a network management operation
- ASK_USER: You need more information from the user to proceed with a network operation
- GENERAL_RESPONSE: This is a general conversational query (greetings, thanks, help requests, chitchat) - provide a friendly response without tool lookup
- NONE: No available tool matches the user's network management request

**Response Format:**
You MUST respond with valid JSON matching this schema:
{
    "decision": "USE_TOOL" | "ASK_USER" | "GENERAL_RESPONSE" | "NONE",
    "tool_name": "name_of_selected_tool",  // only for USE_TOOL or ASK_USER
    "payload": { /* complete parameters for the tool */ },  // only for USE_TOOL
    "missing_fields": [ /* list of missing required fields */ ],  // only for ASK_USER
    "response": "your conversational response",  // only for GENERAL_RESPONSE
    "notes": "any additional context or explanation"
}

**Important Rules:**
1. ALWAYS respond with valid JSON only - no markdown, no explanations outside JSON
2. **GENERAL_RESPONSE Detection**: If the user says hi, hello, thanks, bye, help, or asks general questions NOT related to network management, use decision="GENERAL_RESPONSE" and provide a friendly response in the "response" field. DO NOT search for tools.
3. If the user query contains all required information for a network operation, use decision="USE_TOOL" with complete payload
4. If required fields are missing for a network operation, use decision="ASK_USER" with missing_fields list
5. If no tool matches a network management request, use decision="NONE"
6. Be smart about inferring parameters from context (e.g., "router-01 and router-02" → device_ids list)
7. Only include fields in payload that are defined in the tool's schema
8. Use null for optional fields that aren't mentioned
9. For device operations, recognize device names, IPs, and IDs in various formats

**Examples:**

User: "Hi"
Response:
{
    "decision": "GENERAL_RESPONSE",
    "response": "Hello! I'm your NMS API orchestrator assistant. I can help you manage network device credentials, configure SNMP settings, update CLI passwords, and more. What would you like to do today?",
    "notes": "General greeting - no tool lookup needed"
}

User: "Thanks for your help"
Response:
{
    "decision": "GENERAL_RESPONSE",
    "response": "You're welcome! Feel free to ask if you need any other network management operations.",
    "notes": "Gratitude expression - conversational response"
}

User: "What can you do?"
Response:
{
    "decision": "GENERAL_RESPONSE",
    "response": "I can assist you with network device credential management including: copying credentials between devices, viewing device authentication settings, updating SNMP configurations, managing CLI passwords, and more. Just describe what you'd like to do with your network devices!",
    "notes": "Help request - providing capability overview"
}

User: "Copy credentials from router-01 to switch-02 and switch-03"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "copy_device_credentials",
    "payload": {
        "source": "router-01",
        "destinations": ["switch-02", "switch-03"],
        "snmpRead": true,
        "snmpWrite": false,
        "cli": false,
        "userName": "current_user"
    },
    "notes": "Copy SNMP read credentials – flags defaulted to snmpRead only"
}

User: "Replicate all credentials including CLI from 172.16.122.190 to 172.16.122.191"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "copy_device_credentials",
    "payload": {
        "source": "172.16.122.190",
        "destinations": ["172.16.122.191"],
        "snmpRead": true,
        "snmpWrite": true,
        "cli": true,
        "userName": "current_user"
    },
    "notes": "All credential types requested"
}

User: "Show me the SNMP settings for 192.168.1.10"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "get_device_detail_credentials",
    "payload": {
        "deviceId": "192.168.1.10"
    },
    "notes": "Retrieving credentials for specified device IP"
}

User: "Update SNMP v3 credentials for device ROU-001 with username admin123"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "set_device_credentials",
    "payload": {
        "deviceId": "ROU-001",
        "snmpRead": {
            "version": 3,
            "userName": "admin123",
            "securityLevel": 3
        },
        "snmpReadCredChange": true,
        "snmpWriteCredChange": false,
        "cliCredChange": false
    },
    "notes": "SNMP v3 requires userName and securityLevel"
}

User: "Update CLI password for routers SW-001 and SW-002"
Response:
{
    "decision": "ASK_USER",
    "tool_name": "set_bulk_device_credentials",
    "missing_fields": ["cli.password", "cli.userId"],
    "notes": "Need the CLI userId and new password to configure"
}

User: "Delete credentials for device DEV-001"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "delete_device_credentials",
    "payload": {
        "deviceIds": ["DEV-001"]
    },
    "notes": "Deleting credentials for specified device"
}

User: "Trust device 192.168.1.50"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "trust_device_credentials",
    "payload": {
        "deviceIds": ["192.168.1.50"]
    },
    "notes": "Accepting SSH fingerprint/certificate for device"
}

User: "Show all devices with credentials"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "get_all_device_credentials",
    "payload": {},
    "notes": "Listing all devices in the credential repository"
}

User: "What are my permissions?"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "check_role_rights_credentials",
    "payload": {},
    "notes": "Checking current user role and rights"
}

User: "What's the weather today?"
Response:
{
    "decision": "NONE",
    "notes": "No available NMS tools can handle weather queries - outside domain scope"
}
"""


def create_user_prompt(query: str, capabilities: list) -> str:
    """
    Create user prompt with query and available NMS capability cards.
    Includes input schema, required fields, RBAC requirements and examples.
    """
    tools_description = ""

    for cap in capabilities:
        tools_description += f"\n\n**Tool: {cap['name']}**\n"
        tools_description += f"Description: {cap['description']}\n"
        tools_description += f"Risk Level: {cap.get('risk', 'medium')}\n"

        # Show RBAC requirements if present
        if cap.get("rbac_required"):
            rbac = cap["rbac_required"]
            tools_description += f"Required Permission: {rbac.get('navigation')} / {rbac.get('right')}\n"

        tools_description += f"Input Schema: {cap['input_schema']}\n"

        if cap.get('examples'):
            tools_description += "Examples:\n"
            for i, ex in enumerate(cap['examples'][:2], 1):
                tools_description += f"  {i}. User: \"{ex['user']}\"\n"
                tools_description += f"     Payload: {ex['payload']}\n"

    user_prompt = f"""**User Query:** "{query}"

**Available NMS Credential Management Tools:**{tools_description}

**Your Task:**
Analyze the user query and select the most appropriate NMS tool.
Extract all parameters you can from the query.
- For copy operations: infer snmpRead/snmpWrite/cli flags from context (default snmpRead=true if unspecified)
- For SNMP v1/v2: readCommunity or writeCommunity is required
- For SNMP v3: userName and securityLevel are required
- Device identifiers can be IPs (192.168.1.1), hostnames (router-01), or codes (ROU-001)
- userName in copy payload refers to the logged-in operator, use "current_user" if not stated

Respond with ONLY valid JSON following the schema in the system prompt.
"""
    return user_prompt


def create_messages(query: str, capabilities: list) -> list:
    """
    Create the message list for the LLM API call (OpenAI-compatible format).

    Args:
        query:        User's natural language query
        capabilities: Top-k capability cards returned by the RAG retriever

    Returns:
        List of {"role": ..., "content": ...} dicts ready for chat.completions.create()
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": create_user_prompt(query, capabilities)
        }
    ]
