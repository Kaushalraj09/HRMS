import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self):
        self.APP_ENV: str = os.getenv("APP_ENV", "development").strip().lower()
        self.PROJECT_NAME: str = os.getenv("APP_NAME", "HRMS API")
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")
        self.SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
        self.ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "hrms_access_token")
        self.SESSION_COOKIE_SECURE: bool = _get_bool("SESSION_COOKIE_SECURE", self.APP_ENV == "production")
        self.BACKEND_CORS_ORIGINS: list[str] = [
            origin.strip()
            for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
            if origin.strip()
        ]
        self.FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")
        self.AUTO_CREATE_TABLES: bool = _get_bool("AUTO_CREATE_TABLES", self.APP_ENV == "development")
        self.AUTO_SEED_ROLES: bool = _get_bool("AUTO_SEED_ROLES", self.APP_ENV == "development")
        self.AUTO_SEED_DEMO_DATA: bool = _get_bool("AUTO_SEED_DEMO_DATA", self.APP_ENV == "development")
        self.ENABLE_SCHEDULER: bool = _get_bool("ENABLE_SCHEDULER", self.APP_ENV == "development")
        self.EXPOSE_RESET_LINK_IN_RESPONSE: bool = _get_bool("EXPOSE_RESET_LINK_IN_RESPONSE", False)
        self.SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER: str = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM: str = os.getenv("SMTP_FROM", "")

        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in the environment variables.")
        if not self.SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY is not set in the environment variables.")
        if self.APP_ENV == "production":
            insecure_secret_values = {
                "change_me_use_a_long_random_secret",
                "generate-a-secure-random-secret-key-here",
                "test-secret",
                "change_me_in_production_jwt_secret_min_32_characters_long",
            }
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.lower() in insecure_secret_values or "change_me" in self.SECRET_KEY.lower():
                raise ValueError(
                    "JWT_SECRET_KEY must be a unique, randomly generated value of at least 32 characters in production."
                )
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("BACKEND_CORS_ORIGINS cannot contain '*' in production.")
            if self.ALGORITHM != "HS256":
                raise ValueError("JWT_ALGORITHM must be HS256 in production.")
            if any(not origin.startswith("https://") for origin in self.BACKEND_CORS_ORIGINS):
                raise ValueError("BACKEND_CORS_ORIGINS must use HTTPS in production.")
            if not self.FRONTEND_URL.startswith("https://"):
                raise ValueError("FRONTEND_URL must use HTTPS in production.")
            smtp_values = (self.SMTP_HOST, self.SMTP_USER, self.SMTP_PASSWORD, self.SMTP_FROM)
            if not all(smtp_values) or self.SMTP_HOST == "smtp.example.com" or self.SMTP_PASSWORD == "CHANGE_ME" or "change_me" in self.SMTP_PASSWORD.lower():
                raise ValueError("Production requires valid SMTP configuration for secure account activation and password resets.")


settings = Settings()
