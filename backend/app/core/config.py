import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development").strip().lower()
    PROJECT_NAME: str = os.getenv("APP_NAME", "HRMS API")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BACKEND_CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
        if origin.strip()
    ]
    
    # Frontend Base URL (Production or Staging Domain)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")
    AUTO_CREATE_TABLES: bool = _get_bool("AUTO_CREATE_TABLES", APP_ENV != "production")
    AUTO_SEED_ROLES: bool = _get_bool("AUTO_SEED_ROLES", APP_ENV != "production")
    AUTO_SEED_DEMO_DATA: bool = _get_bool("AUTO_SEED_DEMO_DATA", APP_ENV != "production")
    ENABLE_SCHEDULER: bool = _get_bool("ENABLE_SCHEDULER", APP_ENV != "production")
    EXPOSE_RESET_LINK_IN_RESPONSE: bool = _get_bool("EXPOSE_RESET_LINK_IN_RESPONSE", APP_ENV != "production")
    
    # SMTP email configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")

settings = Settings()
