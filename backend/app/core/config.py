"""
PropIQ Central Configuration
All environment variables and constants in one place.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent  # backend/

# Load .env from backend/ first, then fall back to project root (../)
_env_backend = BASE_DIR / ".env"
_env_root    = BASE_DIR.parent / ".env"
if _env_backend.exists():
    load_dotenv(_env_backend, override=False)
if _env_root.exists():
    load_dotenv(_env_root, override=False)

class Settings:
    # App
    APP_NAME: str = "PropIQ"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Paths
    DATA_DIR: Path = BASE_DIR / "data"
    MODEL_DIR: Path = BASE_DIR / "data" / "models"
    RAW_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"

    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]

    # Model
    MODEL_FILE: str = "propiq_model.pkl"
    MODEL_META_FILE: str = "model_meta.json"

    # Enrichment
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT: int = 8
    GEOCODE_TIMEOUT: int = 5

    # Infra score fallbacks when OSM is unavailable
    INFRA_SCORE_FALLBACK: dict = {
        "prime": 72,
        "mid": 52,
        "peripheral": 32,
    }

    # CV Module
    CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"
    CV_ENABLED: bool = True

    # PDF
    PDF_BRAND_COLOR: str = "#534AB7"
    PDF_TEAL_COLOR: str  = "#0F6E56"


settings = Settings()