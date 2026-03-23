from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "EXAM PORTAL API"
    SECRET_KEY: str = "super-secret-key-change-me-in-production"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "exam_portal"

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
