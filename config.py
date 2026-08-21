"""
Central configuration for NetWatch.

Reads everything from environment variables (loaded from a local .env file
if present). This keeps secrets out of the code and out of git.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # read .env in the project root, if it exists
except ImportError:
    # python-dotenv is optional — without it we just read real env vars.
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# --- Data source ---------------------------------------------------------
# When True, the app serves realistic mock data and needs no credentials.
# When False, it polls the real Aruba Central API using the values below.
USE_MOCK = _as_bool(os.getenv("USE_MOCK"), default=True)

# How often the poller collects a fresh snapshot (seconds).
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))

# --- Database ------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "network_metrics.db"))

# --- Aruba Central API (used only when USE_MOCK is False) ----------------
ARUBA_BASE_URL = os.getenv("ARUBA_BASE_URL", "").rstrip("/")
ARUBA_CLIENT_ID = os.getenv("ARUBA_CLIENT_ID", "")
ARUBA_CLIENT_SECRET = os.getenv("ARUBA_CLIENT_SECRET", "")
ARUBA_ACCESS_TOKEN = os.getenv("ARUBA_ACCESS_TOKEN", "")
ARUBA_REFRESH_TOKEN = os.getenv("ARUBA_REFRESH_TOKEN", "")
ARUBA_CUSTOMER_ID = os.getenv("ARUBA_CUSTOMER_ID", "")

# --- Branding ------------------------------------------------------------
APP_NAME = "NetWatch"
APP_TAGLINE = "Aruba Central Monitor"


def data_source_label():
    """Human-readable label for the active data source."""
    return "mock" if USE_MOCK else "live"
