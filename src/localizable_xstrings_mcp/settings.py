"""Configuration settings for the localizable xstrings MCP server."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI API Configuration
    openai_api_key: str = Field(
        ..., 
        description="OpenAI API key for translation services"
    )
    
    openai_model: str = Field(
        default="gpt-4.1-2025-04-14",
        description="OpenAI model to use for translations"
    )
    
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom OpenAI API base URL (optional)"
    )
    
    # Translation Configuration
    translation_chunk_size: int = Field(
        default=50,
        description="Maximum number of strings per translation request"
    )
    
    translation_temperature: float = Field(
        default=0.3,
        description="Temperature setting for translation model"
    )
    
    translation_max_concurrent_chunks: int = Field(
        default=2,
        description="Maximum number of concurrent translation chunks"
    )
    
    translation_rate_limit_delay: float = Field(
        default=1.0,
        description="Delay in seconds between translation requests"
    )


# Global settings instance
settings = Settings()