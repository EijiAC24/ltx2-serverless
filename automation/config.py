"""
Configuration - loads from environment variables for GitHub Actions
"""

import os

# Grok API
GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL = "grok-2-latest"

# Google Sheets
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
SHEET_NAME = os.environ.get("SHEET_NAME", "prompts")

# Runpod LTX-2
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "j01yykel5de361")
RUNPOD_ENDPOINT = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

# Later API
LATER_API_KEY = os.environ.get("LATER_API_KEY", "")
LATER_PROFILE_ID = os.environ.get("LATER_PROFILE_ID", "")

# FTP (Lolipop)
FTP_SERVER = os.environ.get("FTP_SERVER", "ftp.lolipop.jp")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASSWORD = os.environ.get("FTP_PASSWORD", "")
FTP_PATH = os.environ.get("FTP_PATH", "/buzz/anachronism")
FTP_BASE_URL = os.environ.get("FTP_BASE_URL", "http://okibai.heavy.jp")

# Video generation defaults
DEFAULT_DURATION = 15  # seconds (TikTok optimal: 15s)
DEFAULT_WIDTH = 576
DEFAULT_HEIGHT = 1024
DEFAULT_STEPS = 20

# Daily limits
DAILY_PROMPT_COUNT = 5
DAILY_VIDEO_COUNT = 5

# Polling settings
POLL_INTERVAL = 15  # seconds
MAX_POLL_TIME = 600  # 10 minutes
