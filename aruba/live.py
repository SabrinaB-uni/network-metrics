import requests

import config

SOURCE = "live"

APS_PATH = "/monitoring/v2/aps"
CLIENTS_PATH = "/monitoring/v1/clients/wireless"
TOKEN_PATH = "/oauth2/token"


def _map_ap(a):
    status = "Online" if str(a.get("status", "")).lower() in ("up", "online", "1", "true") else "Offline"
    return {
        "name": a.get("name") or a.get("ap_name") or a.get("serial") or "unknown",
        "location": a.get("site") or a.get("group_name") or a.get("swarm_name") or "",
        "floor": a.get("floor") or "",
        "model": a.get("model") or a.get("ap_model") or "",
        "status": status,
        "clients": int(a.get("client_count") or 0),
        "load_pct": int(a.get("cpu_utilization") or 0),
        "uptime_secs": int(a.get("uptime") or 0),
    }


def _map_client(c):
    conn = str(c.get("connection", "connected")).lower()
    status = "Connected" if conn in ("connected", "wireless", "up", "1") else "Disconnected"
    return {
        "ip": c.get("ip_address") or c.get("ip") or "",
        "hostname": c.get("name") or c.get("hostname") or "",
        "mac": c.get("macaddr") or c.get("mac") or "",
        "username": c.get("username") or "",
        "access_role": c.get("user_role") or c.get("role") or "",
        "vendor": c.get("manufacturer") or c.get("vendor") or "",
        "model_os": c.get("os_type") or c.get("os") or "",
        "status": status,
        "ap_name": c.get("associated_device_name") or c.get("ap_name") or "",
    }


class LiveArubaClient:
    source = SOURCE

    def __init__(self):
        self.base = config.ARUBA_BASE_URL
        self.access_token = config.ARUBA_ACCESS_TOKEN
        self.refresh_token = config.ARUBA_REFRESH_TOKEN

    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"}

    def _refresh(self):
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
            items = self._get(path, {"limit": page, "offset": offset}).get(key) or []
            if not items:
                break
            out.extend(items)
            if len(items) < page:
                break
            offset += page
        return out

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
        except requests.RequestException as exc:
            return False, str(exc)
