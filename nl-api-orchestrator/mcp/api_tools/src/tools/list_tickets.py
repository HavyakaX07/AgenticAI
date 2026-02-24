"""
List tickets tool implementation.
"""
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


async def list_tickets(args: Dict[str, Any], allowlist: list, token: str) -> Dict[str, Any]:
    """
    List support tickets with optional filtering.

    Args:
        args: Filter arguments (status, priority, assignee_id, limit)
        allowlist: List of allowed URL prefixes
        token: API authentication token

    Returns:
        Result with list of tickets
    """
    endpoint = "https://api.example.com/tickets"

    # Check allowlist
    if not any(endpoint.startswith(prefix) for prefix in allowlist):
        logger.error(f"Endpoint {endpoint} not in allowlist")
        raise ValueError(f"Endpoint not allowed: {endpoint}")

    logger.info(f"Listing tickets with filters: {args}")

    # For demo purposes, return mock data
    # In production, this would make a real HTTP request
    try:
        # Mock ticket data
        mock_tickets = [
            {
                "id": "TKT-12345",
                "title": "Payment Gateway Error",
                "description": "Users unable to complete payments",
                "priority": "urgent",
                "status": "open",
                "assignee_id": "user123",
                "created_at": "2026-02-12T10:00:00Z"
            },
            {
                "id": "TKT-12346",
                "title": "Slow Dashboard Loading",
                "description": "Dashboard takes 30+ seconds to load",
                "priority": "medium",
                "status": "in_progress",
                "assignee_id": "user456",
                "created_at": "2026-02-12T11:30:00Z"
            },
            {
                "id": "TKT-12347",
                "title": "Feature Request: Dark Mode",
                "description": "Add dark mode to the application",
                "priority": "low",
                "status": "open",
                "assignee_id": None,
                "created_at": "2026-02-11T15:00:00Z"
            }
        ]

        # Apply filters
        filtered_tickets = mock_tickets

        status_filter = args.get("status", "all")
        if status_filter and status_filter != "all":
            filtered_tickets = [t for t in filtered_tickets if t["status"] == status_filter]

        priority_filter = args.get("priority", "all")
        if priority_filter and priority_filter != "all":
            filtered_tickets = [t for t in filtered_tickets if t["priority"] == priority_filter]

        assignee_filter = args.get("assignee_id")
        if assignee_filter:
            filtered_tickets = [t for t in filtered_tickets if t["assignee_id"] == assignee_filter]

        limit = args.get("limit", 20)
        filtered_tickets = filtered_tickets[:limit]

        logger.info(f"Found {len(filtered_tickets)} tickets")

        return {
            "status": "ok",
            "count": len(filtered_tickets),
            "tickets": filtered_tickets,
            "filters_applied": {
                "status": status_filter,
                "priority": priority_filter,
                "assignee_id": assignee_filter,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Error listing tickets: {e}", exc_info=True)
        raise

