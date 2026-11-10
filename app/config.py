import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "4.0"))

# Service & Networking
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
NONILION_CALLBACK_URL = os.getenv("NONILION_CALLBACK_URL", "")

# Autonomous Fulfillment & Logistics
SHIPPING_STAGE_DELAY_SEC = int(os.getenv("SHIPPING_STAGE_DELAY_SEC", "15"))

# Output Artifact Directory
STATIC_DIR_NAME = os.getenv("STATIC_DIR", "generated_files")
STATIC_DIR = BASE_DIR / STATIC_DIR_NAME
os.makedirs(STATIC_DIR, exist_ok=True)
