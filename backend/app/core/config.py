"""All configuration comes from environment variables (see /.env.example)."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "VitalAI"
    ENVIRONMENT: str = "development"  # development | production
    API_PREFIX: str = "/api/v1"

    # Database: SQLite locally (zero setup), Neon/Supabase Postgres in production.
    DATABASE_URL: str = "sqlite:///./vitalai.db"

    # CORS: comma separated list OR JSON list. Put your Vercel URL here.
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    # Allow every *.vercel.app preview URL too (handy while developing)
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    # --- LLM (optional; any OpenAI-compatible provider) ---
    # Free option: Groq  -> https://console.groq.com  (LLM_API_BASE_URL below)
    # Alternative: Google Gemini's OpenAI-compatible endpoint.
    LLM_API_KEY: str = ""
    LLM_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TIMEOUT_SECONDS: float = 40.0
    LLM_MAX_TOKENS: int = 900
    AGENT_MAX_STEPS: int = 4

    # --- Free public services (no key needed) ---
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT_SECONDS: float = 25.0
    NEARBY_RADIUS_M: int = 3000

    # --- Blood donation rules ---
    DONOR_REST_DAYS: int = 90  # conservative minimum gap between whole-blood donations

    # --- Safety / abuse protection for the free tier ---
    ADMIN_KEY: str = ""  # required for admin endpoints (verify ambulances, etc.)
    CHAT_RATE_LIMIT_PER_MIN: int = 12

    # Emergency numbers shown in the UI (defaults: India). Override per country.
    EMERGENCY_NUMBERS: dict = {
        "country": "India",
        "national_emergency": "112",
        "ambulance": "108",
        "ambulance_alt": "102",
        "women_helpline": "1091",
        "poison_control": "1066",
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str) and not v.strip().startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def sqlalchemy_url(self) -> str:
        url = self.DATABASE_URL
        # Neon/Render hand out "postgres://" or "postgresql://"; SQLAlchemy wants a driver.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def llm_enabled(self) -> bool:
        return bool(self.LLM_API_KEY.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
