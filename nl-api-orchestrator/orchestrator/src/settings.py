"""
Configuration settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # LLM Configuration
    llm_provider: str = "ollama"
    openai_base_url: str = "http://ollama:11434/v1"
    openai_api_key: str = "dummy"
    model_name: str = "llama3.1:8b"

    # Embedding Configuration
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_server_url: str = "http://mcp-embed:9001"

    # MCP Services
    api_tools_url: str = "http://mcp-api:9000"
    opa_url: str = "http://mcp-policy:8181/v1/data/policy"

    # Security
    allowlist_prefixes: str = "https://api.example.com/"
    api_token: str = "demo-token"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://otelcol:4317"
    otel_service_name: str = "nl-api-orchestrator"
    log_level: str = "INFO"

    # Registry
    registry_path: str = "/app/registry/capabilities.json"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowlist_list(self) -> List[str]:
        """Parse allowlist prefixes into a list."""
        return [p.strip() for p in self.allowlist_prefixes.split(",") if p.strip()]


# Global settings instance
settings = Settings()

