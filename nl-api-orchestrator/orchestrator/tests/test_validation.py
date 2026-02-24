"""
Validation tests for payload schema validation and normalization.
"""
import pytest
from src.validators import validate_payload, get_missing_fields
from src.normalizers import normalize_payload


def test_validate_payload_success():
    """Test successful payload validation."""
    payload = {
        "title": "Test Ticket",
        "description": "This is a test description",
        "priority": "high"
    }

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 3},
            "description": {"type": "string", "minLength": 10},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
        },
        "required": ["title", "description", "priority"]
    }

    is_valid, error = validate_payload(payload, schema)
    assert is_valid
    assert error == ""


def test_validate_payload_invalid_enum():
    """Test validation fails for invalid enum value."""
    payload = {
        "title": "Test Ticket",
        "description": "This is a test description",
        "priority": "invalid_priority"  # Not in enum
    }

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
        },
        "required": ["title", "description", "priority"]
    }

    is_valid, error = validate_payload(payload, schema)
    assert not is_valid
    assert "enum" in error.lower() or "invalid_priority" in error


def test_validate_payload_missing_required():
    """Test validation fails for missing required field."""
    payload = {
        "title": "Test Ticket"
        # Missing description and priority
    }

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string"}
        },
        "required": ["title", "description", "priority"]
    }

    is_valid, error = validate_payload(payload, schema)
    assert not is_valid
    assert "required" in error.lower() or "description" in error


def test_validate_payload_min_length():
    """Test validation fails for string too short."""
    payload = {
        "title": "AB",  # Too short (minLength: 3)
        "description": "Test description",
        "priority": "high"
    }

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 3},
            "description": {"type": "string"},
            "priority": {"type": "string"}
        },
        "required": ["title", "description", "priority"]
    }

    is_valid, error = validate_payload(payload, schema)
    assert not is_valid


def test_get_missing_fields():
    """Test missing fields detection."""
    payload = {
        "title": "Test"
    }

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string"}
        },
        "required": ["title", "description", "priority"]
    }

    missing = get_missing_fields(payload, schema)
    assert "description" in missing
    assert "priority" in missing
    assert "title" not in missing


def test_normalize_priority():
    """Test priority normalization."""
    payload = {
        "title": "Test",
        "description": "Test description",
        "priority": "asap"  # Should normalize to "urgent"
    }

    capability = {
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
            }
        }
    }

    normalized = normalize_payload(payload, capability)
    assert normalized["priority"] == "urgent"


def test_normalize_status():
    """Test status normalization."""
    payload = {
        "status": "active"  # Should normalize to "open"
    }

    capability = {
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["open", "in_progress", "closed"]}
            }
        }
    }

    normalized = normalize_payload(payload, capability)
    assert normalized["status"] == "open"


def test_normalize_trim_strings():
    """Test string trimming."""
    payload = {
        "title": "  Test Title  ",
        "description": "  Test Description  "
    }

    capability = {
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    }

    normalized = normalize_payload(payload, capability)
    assert normalized["title"] == "Test Title"
    assert normalized["description"] == "Test Description"


def test_normalize_multiple_fields():
    """Test normalizing multiple fields at once."""
    payload = {
        "title": "  Test  ",
        "priority": "critical",  # → urgent
        "status": "done"  # → closed
    }

    capability = {
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"}
            }
        }
    }

    normalized = normalize_payload(payload, capability)
    assert normalized["title"] == "Test"
    assert normalized["priority"] == "urgent"
    assert normalized["status"] == "closed"

