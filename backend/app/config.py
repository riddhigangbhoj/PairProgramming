"""
Application configuration.
Loads settings from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Create a .env file to override defaults.
    """

    # Database
    DATABASE_URL: str = "sqlite:///./pair_programming.db"

    # CORS - origins allowed to access the API
    # Can be set as comma-separated string in env: "origin1,origin2,origin3"
    ALLOWED_ORIGINS: Union[List[str], str] = [
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Production domains
        "https://pairprogramming.riddhigangbhoj.com",
        "https://riddhigangbhoj.com",
        "https://www.riddhigangbhoj.com",
        "https://api.riddhigangbhoj.com",
    ]

    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # Application
    DEBUG: bool = False  # Secure by default - set to True in .env for development
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-ME-IN-PRODUCTION")

    # AI/Autocomplete (placeholder for future integration)
    AI_MODEL: str = "mock"
    AI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()