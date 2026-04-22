"""config.py

This module provides configuration settings for the frontend service.

Key Features:
- Host and port settings for the frontend UI server.
- Backend URL resolution from environment variables.

"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    frontend_host: str = "127.0.0.1"
    frontend_port: int = 3030

    backend_host: str = "127.0.0.1"
    backend_port: int = 3000

    def get_backend_url(self):
        if hasattr(self, "backend_url"):
            return self.backend_url
        return f"http://{self.backend_host}:{self.backend_port}"


settings = Settings()
