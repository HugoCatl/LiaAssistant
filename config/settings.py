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
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_model_reasoning: str = Field("gemini-2.5-pro", validation_alias="GEMINI_MODEL_REASONING")

    # Local storage (Obsidian vault path)
    obsidian_vault_path: Optional[Path] = Field(None, validation_alias="OBSIDIAN_VAULT_PATH")

    # STT Model path or model size
    whisper_model_path: str = Field("base", validation_alias="WHISPER_MODEL_PATH")

    # TTS configuration
    tts_enabled: bool = Field(True, validation_alias="TTS_ENABLED")
    tts_voice: str = Field("es-ES-ElviraNeural", validation_alias="TTS_VOICE")

    # General configuration
    debug: bool = Field(False, validation_alias="DEBUG")

    # User Profile settings (parameterizes personal data)
    user_name: str = Field("Usuario", validation_alias="USER_NAME")
    user_age: str = Field("20", validation_alias="USER_AGE")
    user_profile: str = Field("Usuario", validation_alias="USER_PROFILE")

# Instantiated settings object
settings = Settings()
