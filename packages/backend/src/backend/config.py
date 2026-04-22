"""config.py

This module provides configuration settings for the backend service.

Key Features:
- LLM provider, model, and API key settings.
- Backend, MCP, and MongoDB connection settings.
- Agent execution defaults.

"""

from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = False
    groq_api_key: str = ""

    # LLM Configuration
    llm_provider: Literal["groq"] | Literal["openai_compatible"] = "groq"
    llm_api_base: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"

    # Backend settings
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # MCP settings
    mcp_url: Optional[str] = None
    mcp_host: str = "10.8.0.50"
    mcp_port: int = 5000

    # Database settings
    database_url: Optional[str] = None
    database_user: Optional[str] = None
    database_pass: Optional[str] = None
    database_host: str = "127.0.0.1"
    database_port: int = 10260
    database_name: str = "main"

    database_insecure_tls: bool = False

    # Agent execution settings
    auto_execute_commands: bool = True
    default_executor_container: str = "A-10.8.0.99"

    def get_mcp_url(self):
        if self.mcp_url:
            return self.mcp_url
        return f"http://{self.mcp_host}:{self.mcp_port}"

    def get_database_url(self):
        if self.database_url:
            return self.database_url
        if self.database_user and self.database_pass:
            tls = "?tls=true&tlsInsecure=true" if self.database_insecure_tls else ""
            return f"mongodb://{self.database_user}:{self.database_pass}@{self.database_host}:{self.database_port}/{self.database_name}{tls}"
        return (
            f"mongodb://{self.database_host}:{self.database_port}/{self.database_name}"
        )


settings = Settings()
