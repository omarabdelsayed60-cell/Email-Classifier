import os
from pathlib import Path
from dotenv import load_dotenv

# Project base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from base directory with override=True
load_dotenv(BASE_DIR / ".env", override=True)


class Config:
    """Class-based environment configuration loader."""

    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    SCREENSHOTS_DIR: Path = BASE_DIR / "screenshots"
    DATABASE_PATH: Path = DATA_DIR / "emails.db"

    @classmethod
    def get_gemini_api_key(cls) -> str:
        """Dynamically reloads .env and returns the current GEMINI_API_KEY."""
        load_dotenv(cls.BASE_DIR / ".env", override=True)
        return os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get_gemini_api_key()


# Ensure required application directories exist automatically
Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
