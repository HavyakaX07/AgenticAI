"""
Tools registry.
Import and register all available tools here.
"""
from .create_ticket import create_ticket
from .list_tickets import list_tickets

# Registry of all available tools
TOOLS = {
    "create_ticket": create_ticket,
    "list_tickets": list_tickets,
}

__all__ = ["TOOLS", "create_ticket", "list_tickets"]

