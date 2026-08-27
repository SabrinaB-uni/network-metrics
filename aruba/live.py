import time

import requests

import config

SOURCE = "live"

# New Central runs on HPE GreenLake: get a bearer token from GreenLake SSO with
# the client id/secret, then call the regional Central API with it.
TOKEN_URL = "https://sso.common.cloud.hpe.com/as/token.oauth2"
APS_PATH = "/network-monitoring/v1/aps"
CLIENTS_PATH = "/network-monitoring/v1/clients"


def _map_ap(a):
    return {
        "name": a.get("deviceName") or a.get("serialNumber") or "unknown",
        "location": a.get("siteName") or "",
        "floor": "",
        "model": a.get("model") or "",
        "status": "Online" if str(a.get("status", "")).upper() == "ONLINE" else "Offline",
        "clients": int(a.get("clientCount") or 0),
        "load_pct": int(a.get("cpuUtilization") or 0),
        "uptime_secs": int((a.get("uptimeInMillis") or 0) / 1000),
    }


def _map_client(c):
    return {
        "ip": c.get("ipv4") or "",
        "hostname": c.get("hostName") or "",
        "mac": c.get("macAddress") or "",
        "username": c.get("userName") or "",
        "access_role": c.get("role") or "",
        "vendor": c.get("clientManufacturer") or c.get("clientVendor") or "",
        "model_os": c.get("clientOperatingSystem") or "",
        "status": "Connected" if str(c.get("status", "")).lower() == "connected" else "Disconnected",
        "ap_name": c.get("connectedTo") or "",
    }


class LiveArubaClient:
    source = SOURCE

    def __init__(self):
        self.base = config.ARUBA_BASE_URL
        self._token = None
        self._expiry = 0

    def _token_header(self):
        if not self._token or time.time() > self._expiry - 60:
            r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials"},
                              auth=(config.ARUBA_CLIENT_ID, config.ARUBA_CLIENT_SECRET),
                              timeout=30)
            r.raise_for_status()
            data = r.json()
            self._token = data["access_token"]
            self._expiry = time.time() + int(data.get("expires_in", 3600))
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, path, params):
        r = requests.get(f"{self.base}{path}", headers=self._token_header(),
                         params=params, timeout=30)
        if r.status_code == 401:
            self._token = None
            r = requests.get(f"{self.base}{path}", headers=self._token_header(),
                             params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _all(self, path, page=1000, cap=20000):
        out, offset = [], 0
        while len(out) < cap:
            data = self._get(path, {"limit": page, "offset": offset})
            items = data.get("items") or []
            out.extend(items)
            offset += len(items)
            if len(items) < page or offset >= (data.get("total") or 0):
                break
        return out

    def get_access_points(self):
        return [_map_ap(a) for a in self._all(APS_PATH)]

    def get_clients(self):
        return [_map_client(c) for c in self._all(CLIENTS_PATH)]

    def collect(self):
        return self.get_access_points(), self.get_clients()

    def test_connection(self):
        if not (self.base and config.ARUBA_CLIENT_ID and config.ARUBA_CLIENT_SECRET):
            return False, "Missing ARUBA_BASE_URL / CLIENT_ID / CLIENT_SECRET in .env"
        try:
            self._get(APS_PATH, {"limit": 1})
            return True, "Connected to Aruba Central."
        except requests.RequestException as exc:
            return False, str(exc)
