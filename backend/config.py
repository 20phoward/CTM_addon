import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "storage" / "audio")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'calls.db'}")
# Render uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"}
MAX_UPLOAD_SIZE_MB = 500

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# CTM Integration
CTM_WEBHOOK_SECRET = os.getenv("CTM_WEBHOOK_SECRET", "")

# Google Ads (Phase 4)
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
GOOGLE_ADS_DRY_RUN = os.getenv("GOOGLE_ADS_DRY_RUN", "true").lower() in ("true", "1", "yes")
GOOGLE_ADS_CONVERSION_ACTION = os.getenv("GOOGLE_ADS_CONVERSION_ACTION", "")
