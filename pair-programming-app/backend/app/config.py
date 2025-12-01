"""
Application configuration.
Loads settings from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Create a .env file to override defaults.
    """
    
    # Database
    DATABASE_URL: str = "sqlite:///./pair_programming.db"
    
    # CORS - origins allowed to access the API
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
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