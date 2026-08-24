import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


USE_MOCK = _as_bool(os.getenv("USE_MOCK"), True)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "network_metrics.db"))

ARUBA_BASE_URL = os.getenv("ARUBA_BASE_URL", "").rstrip("/")
ARUBA_CLIENT_ID = os.getenv("ARUBA_CLIENT_ID", "")
ARUBA_CLIENT_SECRET = os.getenv("ARUBA_CLIENT_SECRET", "")
ARUBA_ACCESS_TOKEN = os.getenv("ARUBA_ACCESS_TOKEN", "")
ARUBA_REFRESH_TOKEN = os.getenv("ARUBA_REFRESH_TOKEN", "")
ARUBA_CUSTOMER_ID = os.getenv("ARUBA_CUSTOMER_ID", "")

APP_NAME = "network metrics"
APP_TAGLINE = "Aruba Central monitor"


def data_source_label():
    return "mock" if USE_MOCK else "live"
