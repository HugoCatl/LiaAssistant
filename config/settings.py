import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    Validates core paths and credentials needed for the assistant.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core API Keys
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-3.5-flash", validation_alias="GEMINI_MODEL")

    # Local storage (Obsidian vault path)
    obsidian_vault_path: Optional[Path] = Field(None, validation_alias="OBSIDIAN_VAULT_PATH")

    # STT Model path or model size
    whisper_model_path: str = Field("base", validation_alias="WHISPER_MODEL_PATH")

    # General configuration
    debug: bool = Field(False, validation_alias="DEBUG")

# Instantiated settings object
settings = Settings()
