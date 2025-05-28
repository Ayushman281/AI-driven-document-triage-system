import os
import logging
import re
from dotenv import load_dotenv

# Determine the base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

# Log the environment variables for debugging
logging.info(f"Loading environment from: {env_path}")

# IMPORTANT: Remove any default values that could override your .env settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_here":
    # If not set or using placeholder, manually read from .env as a fallback
    try:
        with open(env_path, 'r') as file:
            for line in file:
                if line.strip().startswith('OPENROUTER_API_KEY='):
                    OPENROUTER_API_KEY = line.strip().split('=', 1)[1].strip()
                    # Remove any quotes if present
                    if (OPENROUTER_API_KEY.startswith('"') and OPENROUTER_API_KEY.endswith('"')) or \
                       (OPENROUTER_API_KEY.startswith("'") and OPENROUTER_API_KEY.endswith("'")):
                        OPENROUTER_API_KEY = OPENROUTER_API_KEY[1:-1]
                    break
    except Exception as e:
        logging.error(f"Error reading .env file directly: {e}")

# Get other configuration values
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mistralai/mistral-7b-instruct:free")

# Log masked API key for debugging
if OPENROUTER_API_KEY:
    masked_key = f"{OPENROUTER_API_KEY[:8]}...{OPENROUTER_API_KEY[-4:]}" if len(OPENROUTER_API_KEY) > 12 else "[too short]"
    logging.debug(f"Loaded API key: {masked_key}")
else:
    logging.error("No API key found in environment or .env file!")

# Database configuration  
DATABASE_PATH = os.getenv("DATABASE_PATH", "./database/triage.db")

# Make DATABASE_PATH absolute if it's relative
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_PATH)

# Ensure the database directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(levelname)s: %(message)s"
)
