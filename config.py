import os
import secrets

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "network_metrics.db"))

ARUBA_BASE_URL = os.getenv("ARUBA_BASE_URL", "").rstrip("/")
ARUBA_CLIENT_ID = os.getenv("ARUBA_CLIENT_ID", "")
ARUBA_CLIENT_SECRET = os.getenv("ARUBA_CLIENT_SECRET", "")

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

# Optional: a Slack incoming-webhook URL to push alerts to.
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

APP_NAME = "network metrics"
APP_TAGLINE = "Aruba Central monitor"
