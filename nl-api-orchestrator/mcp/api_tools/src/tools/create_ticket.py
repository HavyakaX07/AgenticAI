"""
Create ticket tool implementation.
"""
import logging
import uuid
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


async def create_ticket(args: Dict[str, Any], allowlist: list, token: str) -> Dict[str, Any]:
    """
    Create a support ticket.

    Args:
        args: Ticket arguments (title, description, priority, assignee_id)
        allowlist: List of allowed URL prefixes
        token: API authentication token

    Returns:
        Result with ticket_id
    """
    endpoint = "https://api.example.com/tickets"

    # Check allowlist
    if not any(endpoint.startswith(prefix) for prefix in allowlist):
        logger.error(f"Endpoint {endpoint} not in allowlist")
        raise ValueError(f"Endpoint not allowed: {endpoint}")

    logger.info(f"Creating ticket: {args.get('title')}")

    # For demo purposes, mock the API call
    # In production, this would make a real HTTP request
    try:
        # Mock API response
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

        # Simulate API call (commented out for local demo)
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         endpoint,
        #         json=args,
        #         headers={"Authorization": f"Bearer {token}"},
        #         timeout=30.0
        #     )
        #     response.raise_for_status()
        #     result = response.json()
        #     ticket_id = result.get("id", ticket_id)

        logger.info(f"Ticket created: {ticket_id}")

        return {
            "status": "ok",
            "ticket_id": ticket_id,
            "title": args.get("title"),
            "priority": args.get("priority"),
            "created_at": "2026-02-12T14:30:00Z"
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error creating ticket: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        raise

