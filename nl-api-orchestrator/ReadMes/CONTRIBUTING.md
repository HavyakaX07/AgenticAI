# Contributing to NL → API Orchestrator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Getting Started

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (for local development)
- Git

### Development Setup

1. **Fork and clone:**
   ```bash
   git clone https://github.com/your-username/nl-api-orchestrator.git
   cd nl-api-orchestrator
   ```

2. **Create environment:**
   ```bash
   cp .env.example .env
   ```

3. **Start services:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify setup:**
   ```bash
   curl http://localhost:8080/health
   ```

## Development Workflow

### Making Changes

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow code style guidelines (see below)
   - Add tests for new functionality
   - Update documentation

3. **Test locally:**
   ```bash
   # Run unit tests
   docker compose run --rm orchestrator pytest tests/ -v
   
   # Run integration tests
   ./test.sh  # or test.ps1 on Windows
   ```

4. **Commit:**
   ```bash
   git add .
   git commit -m "feat: add new capability for X"
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Maintenance tasks

**Examples:**
```
feat: add email notification tool
fix: handle null values in normalizer
docs: update quick start guide
test: add validation edge cases
```

## Code Style

### Python

**Style Guide:** PEP 8

**Tools:**
- `black` for formatting (line length: 100)
- `isort` for import sorting
- `flake8` for linting
- `mypy` for type checking

**Run formatters:**
```bash
black orchestrator/src/
isort orchestrator/src/
flake8 orchestrator/src/
```

**Type Hints:**
Always use type hints for function signatures:
```python
def process_data(input: Dict[str, Any], config: Config) -> Result:
    ...
```

**Docstrings:**
Use Google-style docstrings:
```python
def calculate_score(query: str, capability: Dict) -> float:
    """
    Calculate relevance score between query and capability.
    
    Args:
        query: User's natural language query
        capability: Capability card dictionary
    
    Returns:
        Relevance score between 0 and 1
    
    Raises:
        ValueError: If capability is missing required fields
    """
    ...
```

### Configuration Files

- **YAML:** 2-space indentation
- **JSON:** 2-space indentation, trailing commas allowed
- **Docker:** Follow official best practices

## Testing Guidelines

### Unit Tests

**Location:** `orchestrator/tests/`

**Requirements:**
- Test happy path
- Test edge cases
- Test error handling
- Mock external dependencies

**Example:**
```python
import pytest
from src.validators import validate_payload

def test_validate_payload_success():
    payload = {"title": "Test", "priority": "high"}
    schema = {...}
    is_valid, error = validate_payload(payload, schema)
    assert is_valid
    assert error == ""

def test_validate_payload_invalid_enum():
    payload = {"priority": "invalid"}
    schema = {...}
    is_valid, error = validate_payload(payload, schema)
    assert not is_valid
    assert "enum" in error.lower()
```

### Integration Tests

**Location:** `test.sh` / `test.ps1`

Add new test scenarios to the test scripts:
```bash
echo "Test N: Your New Test"
echo "---------------------"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"your test query"}' | jq
```

### Test Coverage

**Target:** 80%+ code coverage

**Run with coverage:**
```bash
docker compose run --rm orchestrator pytest tests/ --cov=src --cov-report=html
```

## Adding New Features

### Adding a New Tool

1. **Create tool implementation:**
   ```python
   # mcp/api_tools/src/tools/your_tool.py
   async def your_tool(args: Dict[str, Any], allowlist: list, token: str) -> Dict[str, Any]:
       """
       Your tool description.
       
       Args:
           args: Tool arguments
           allowlist: Allowed URL prefixes
           token: API authentication token
       
       Returns:
           Result dictionary
       """
       # Implementation
       pass
   ```

2. **Register tool:**
   ```python
   # mcp/api_tools/src/tools/__init__.py
   from .your_tool import your_tool
   
   TOOLS = {
       # ...existing tools...
       "your_tool": your_tool,
   }
   ```

3. **Add capability card:**
   ```json
   // orchestrator/registry/capabilities.json
   {
     "name": "your_tool",
     "description": "Detailed description of what your tool does",
     "endpoint": "POST https://api.example.com/your-endpoint",
     "auth": "bearer",
     "risk": "low|medium|high",
     "input_schema": {
       "type": "object",
       "properties": {...},
       "required": [...]
     },
     "examples": [
       {
         "user": "Example query",
         "payload": {...}
       }
     ]
   }
   ```

4. **Add tests:**
   ```python
   # orchestrator/tests/test_your_tool.py
   def test_your_tool():
       ...
   ```

5. **Update documentation:**
   - Add to README.md examples
   - Update ARCHITECTURE.md if architectural changes

### Adding a New Normalizer

```python
# orchestrator/src/normalizers.py

# Add mapping
YOUR_FIELD_MAP = {
    "synonym1": "canonical1",
    "synonym2": "canonical2",
}

# Update normalize_payload function
def normalize_payload(payload: Dict[str, Any], capability: Dict[str, Any]) -> Dict[str, Any]:
    # ...existing code...
    
    # Add your normalization
    if "your_field" in properties and "your_field" in normalized:
        original = normalized["your_field"]
        if isinstance(original, str):
            lower_val = original.lower().strip()
            if lower_val in YOUR_FIELD_MAP:
                normalized["your_field"] = YOUR_FIELD_MAP[lower_val]
```

### Adding a New Policy

```rego
# mcp/policy/policy.rego

# Add new rule
allow {
    input.tool == "your_tool"
    input.payload.required_field
    # Your conditions
}

reason = msg {
    not allow
    input.tool == "your_tool"
    msg := "Your descriptive reason"
}
```

## Documentation

### When to Update Docs

- **README.md:** User-facing changes, new features, setup changes
- **ARCHITECTURE.md:** Architectural decisions, component changes
- **CONTRIBUTING.md:** Process changes, new guidelines
- **Code comments:** Complex logic, non-obvious behavior

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams for complex flows (Mermaid)
- Keep examples up-to-date

## Review Process

### Before Submitting PR

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main
- [ ] PR description explains changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
```

### Review Criteria

Reviewers will check:
1. **Functionality:** Does it work as intended?
2. **Tests:** Are there adequate tests?
3. **Code Quality:** Is it readable and maintainable?
4. **Documentation:** Is it documented?
5. **Security:** Are there security implications?

## Release Process

Releases follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Credit contributions appropriately

### Getting Help

- **Issues:** For bugs and feature requests
- **Discussions:** For questions and ideas
- **Discord/Slack:** For real-time chat (if available)

### Recognition

Contributors are recognized in:
- Release notes
- CONTRIBUTORS.md file
- Project README

## Common Tasks

### Updating Dependencies

```bash
# Update Python dependencies
cd orchestrator
pip install -U package-name
pip freeze > requirements.txt

# Test changes
docker compose up -d --build orchestrator
./test.sh
```

### Adding Environment Variable

1. Add to `.env.example`
2. Add to `orchestrator/src/settings.py`
3. Update `docker-compose.yml` if needed
4. Document in README.md

### Debugging Services

```bash
# View logs
docker compose logs -f orchestrator

# Enter container
docker compose exec orchestrator bash

# Restart service
docker compose restart orchestrator

# Rebuild service
docker compose up -d --build orchestrator
```

## Questions?

If you have questions not covered here:
1. Check existing issues/discussions
2. Review documentation (README, ARCHITECTURE)
3. Ask in discussions or Discord
4. Open an issue with the "question" label

---

Thank you for contributing! 🎉

