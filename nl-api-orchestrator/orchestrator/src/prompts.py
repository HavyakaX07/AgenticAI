"""
LLM prompts for tool selection and payload filling.
"""

# JSON schema for LLM response
LLM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["USE_TOOL", "ASK_USER", "NONE"],
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
        "notes": {
            "type": "string",
            "description": "Additional notes or explanation"
        }
    },
    "required": ["decision"]
}


SYSTEM_PROMPT = """You are an intelligent API orchestrator assistant. Your job is to:

1. Understand the user's natural language request
2. Select the most appropriate API tool from the available options
3. Extract and structure the required parameters from the user's query
4. Return a strict JSON response with your decision

**Available Decisions:**
- USE_TOOL: You have all required information to execute the tool
- ASK_USER: You need more information from the user to proceed
- NONE: No available tool matches the user's request

**Response Format:**
You MUST respond with valid JSON matching this schema:
{
    "decision": "USE_TOOL" | "ASK_USER" | "NONE",
    "tool_name": "name_of_selected_tool",
    "payload": { /* complete parameters for the tool */ },
    "missing_fields": [ /* list of missing required fields */ ],
    "notes": "any additional context or explanation"
}

**Important Rules:**
1. ALWAYS respond with valid JSON only - no markdown, no explanations outside JSON
2. If the user query contains all required information, use decision="USE_TOOL" with complete payload
3. If required fields are missing, use decision="ASK_USER" with missing_fields list
4. If no tool matches the request, use decision="NONE"
5. Use the tool descriptions and examples to guide parameter extraction
6. Be smart about inferring parameters from context (e.g., "urgent" → priority="urgent")
7. Only include fields in payload that are defined in the tool's schema
8. Use null for optional fields that aren't mentioned

**Examples:**

User: "Create urgent ticket for API downtime"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "create_ticket",
    "payload": {
        "title": "API Downtime",
        "description": "Urgent issue reported regarding API availability",
        "priority": "urgent"
    },
    "notes": "Created ticket with inferred details"
}

User: "Show me tickets"
Response:
{
    "decision": "USE_TOOL",
    "tool_name": "list_tickets",
    "payload": {
        "status": "all",
        "limit": 20
    },
    "notes": "Listing all tickets with default limit"
}

User: "Create a ticket"
Response:
{
    "decision": "ASK_USER",
    "tool_name": "create_ticket",
    "missing_fields": ["title", "description", "priority"],
    "notes": "Need more details about what the ticket should be for"
}

User: "What's the weather today?"
Response:
{
    "decision": "NONE",
    "notes": "No available tools can handle weather queries"
}
"""


def create_user_prompt(query: str, capabilities: list) -> str:
    """
    Create user prompt with query and available capabilities.

    Args:
        query: User's natural language query
        capabilities: List of candidate capability cards

    Returns:
        Formatted user prompt
    """
    tools_description = ""

    for cap in capabilities:
        tools_description += f"\n\n**Tool: {cap['name']}**\n"
        tools_description += f"Description: {cap['description']}\n"
        tools_description += f"Risk Level: {cap.get('risk', 'medium')}\n"
        tools_description += f"Input Schema: {cap['input_schema']}\n"

        if cap.get('examples'):
            tools_description += "Examples:\n"
            for i, ex in enumerate(cap['examples'][:2], 1):  # Show max 2 examples
                tools_description += f"  {i}. User: \"{ex['user']}\"\n"
                tools_description += f"     Payload: {ex['payload']}\n"

    user_prompt = f"""**User Query:** "{query}"

**Available Tools:**{tools_description}

**Your Task:**
Analyze the user query and select the most appropriate tool. Extract all parameters you can from the query.
Respond with ONLY valid JSON following the schema provided in the system prompt.
"""

    return user_prompt


def create_messages(query: str, capabilities: list) -> list:
    """
    Create message list for LLM API call.

    Args:
        query: User's natural language query
        capabilities: List of candidate capability cards

    Returns:
        List of message dicts for OpenAI-compatible API
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

