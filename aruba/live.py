"""
Live HPE Aruba Networking Central client.

Talks to the real monitoring API using the credentials in your .env. It exposes
the exact same interface as MockArubaClient (`collect()` -> (aps, clients)), so
the rest of the app is identical whether it runs on mock or live data.

NOTE ON FIELD NAMES: Aruba Central's JSON field names vary slightly by API
version/firmware. The `_map_*` helpers below use defensive `.get()` fallbacks;
if a field comes through empty against your tenant, adjust the mapping here.
Only read-only GET monitoring endpoints are used.
"""
from __future__ import annotations

import requests

import config

SOURCE = "live"

APS_PATH = "/monitoring/v2/aps"
CLIENTS_PATH = "/monitoring/v1/clients/wireless"
TOKEN_PATH = "/oauth2/token"


def _map_ap(a: dict) -> dict:
    status_raw = str(a.get("status", "")).lower()
    status = "Online" if status_raw in ("up", "online", "1", "true") else "Offline"
    return {
        "name": a.get("name") or a.get("ap_name") or a.get("serial") or "unknown",
        "location": a.get("site") or a.get("group_name") or a.get("swarm_name") or "",
        "floor": a.get("floor") or a.get("labels") or "",
        "model": a.get("model") or a.get("ap_model") or "",
        "status": status,
        "clients": int(a.get("client_count") or 0),
        "load_pct": int(a.get("cpu_utilization") or 0),
        "uptime_secs": int(a.get("uptime") or 0),
    }


def _map_client(c: dict) -> dict:
    conn_raw = str(c.get("connection", "connected")).lower()
    status = "Connected" if conn_raw in ("connected", "wireless", "up", "1") else "Disconnected"
    return {
        "ip": c.get("ip_address") or c.get("ip") or "",
        "hostname": c.get("name") or c.get("hostname") or "",
        "mac": c.get("macaddr") or c.get("mac") or "",
        "username": c.get("username") or "",
        "access_role": c.get("user_role") or c.get("role") or "",
        "vendor": c.get("manufacturer") or c.get("vendor") or "",
        "model_os": c.get("os_type") or c.get("os") or "",
        "status": status,
        "ap_name": c.get("associated_device_name") or c.get("ap_name")
        or c.get("connected_device") or "",
    }


class LiveArubaClient:
    source = SOURCE

    def __init__(self):
        self.base = config.ARUBA_BASE_URL
        self.access_token = config.ARUBA_ACCESS_TOKEN
        self.refresh_token = config.ARUBA_REFRESH_TOKEN

    # --- auth -----------------------------------------------------------
    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"}

    def _refresh(self):
        """Exchange the refresh token for a new access token (kept in memory)."""
        resp = requests.post(
            f"{self.base}{TOKEN_PATH}",
            params={
                "client_id": config.ARUBA_CLIENT_ID,
                "client_secret": config.ARUBA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)

    # --- requests -------------------------------------------------------
    def _get(self, path, params=None):
        url = f"{self.base}{path}"
        r = requests.get(url, headers=self._headers(), params=params, timeout=30)
        if r.status_code == 401 and self.refresh_token:
            self._refresh()
            r = requests.get(url, headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _paginate(self, path, key, page=500, cap=20000):
        out, offset = [], 0
        while len(out) < cap:
            data = self._get(path, {"limit": page, "offset": offset})
            items = data.get(key) or []
            if not items:
                break
            out.extend(items)
            if len(items) < page:
                break
            offset += page
        return out

    # --- public interface ----------------------------------------------
    def get_access_points(self):
        return [_map_ap(a) for a in self._paginate(APS_PATH, "aps")]

    def get_clients(self):
        return [_map_client(c) for c in self._paginate(CLIENTS_PATH, "clients")]

    def collect(self):
        return self.get_access_points(), self.get_clients()

    def test_connection(self):
        if not self.base or not self.access_token:
            return False, "Missing ARUBA_BASE_URL or ARUBA_ACCESS_TOKEN in .env"
        try:
            self._get(APS_PATH, {"limit": 1})
            return True, "Connected to Aruba Central."
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            return False, f"{type(exc).__name__}: {exc}"
