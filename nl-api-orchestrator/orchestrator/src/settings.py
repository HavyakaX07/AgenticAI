"""
Configuration settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # LLM Configuration
    # Ollama runs on the HOST machine (not in Docker).
    # Docker Desktop (Windows/macOS) resolves host.docker.internal to the host.
    # On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` in compose (already done).
    llm_provider: str = "ollama"
    openai_base_url: str = "http://host.docker.internal:11434/v1"
    openai_api_key: str = "ollama"   # Ollama ignores the key but openai client requires a value
    model_name: str = "llama3.2:3b"

    # Embedding Configuration
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_server_url: str = "http://mcp-embed:9001"

    # MCP Services
    api_tools_url: str = "http://mcp-api:9000"
    opa_url: str = "http://mcp-policy:8181/v1/data/policy"

    # Device Resolver
    # ── Backend options: "mock" | "sqlite" | "postgres" | "rest" ──────────────
    # mock    : in-memory mock data (POC, no external dependency)
    # sqlite  : lightweight file-based DB (on-prem / single-server)
    # postgres: production PostgreSQL
    # rest    : call NMS REST API (set nms_device_api_url)
    nms_device_api_url: str  = ""           # used when db_backend=rest
    device_resolver_mock: bool = False       # legacy compat — overrides to "mock"
    db_backend:   str = "postgres"              # mock | sqlite | postgres | rest
    db_url:       str = ""                  # postgresql://user:pass@host:5432/nmsdb
    sqlite_path:  str = "/data/devices.db"  # path for sqlite backend

    # Security
    allowlist_prefixes: str = "https://api.example.com/"
    api_token: str = "demo-token"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://otelcol:4317"
    otel_service_name: str = "nl-api-orchestrator"
    log_level: str = "INFO"

    # Registry – all three NMS data sources
    registry_path: str = "/app/registry/credential_api_schema_rag.json"
    registry_dir: str = "/app/registry"
    nlp_metadata_path: str = "/app/registry/credential_api_nlp_metadata.json"
    training_examples_path: str = "/app/registry/credential_api_rag_training_examples.json"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowlist_list(self) -> List[str]:
        """Parse allowlist prefixes into a list."""
        return [p.strip() for p in self.allowlist_prefixes.split(",") if p.strip()]


# Global settings instance
settings = Settings()

