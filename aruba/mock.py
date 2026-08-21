"""
Mock Aruba Central client.

Produces realistic, self-consistent access-point and client data so the whole
app runs with no credentials. It exposes the SAME interface as the live client
(`collect()` returns a `(access_points, clients)` tuple), so the rest of the
app cannot tell them apart — swapping to live is a one-line change.

`snapshot(when)` is deterministic for a given timestamp, which lets the seed
script build a believable day of history.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

SOURCE = "mock"

# --- Access-point roster: 24 APs across a building, 3 deliberately offline ---
# (name, location, floor, model, peak_clients, capacity, offline)
_ROSTER = [
    ("AP-101-Reception", "Lobby",         "Floor 1", "AP-515", 40, 46, False),
    ("AP-102-OpenPlan",  "Open Office",    "Floor 1", "AP-515", 35, 42, False),
    ("AP-103-Meeting",   "Meeting Rm A",   "Floor 1", "AP-305",  0,  1, True),
    ("AP-104-Canteen",   "Canteen",        "Floor 1", "AP-515", 28, 40, False),
    ("AP-105-Warehouse", "Warehouse",      "Floor 1", "AP-505", 12, 24, False),
    ("AP-201-ConfRoom",  "Conference",     "Floor 2", "AP-515", 30, 40, False),
    ("AP-202-DevZone",   "Dev Area",       "Floor 2", "AP-635", 52, 56, False),
    ("AP-203-Breakout",  "Breakout",       "Floor 2", "AP-515", 18, 32, False),
    ("AP-204-QALab",     "QA Lab",         "Floor 2", "AP-515", 22, 34, False),
    ("AP-205-Server",    "Server Room",    "Floor 2", "AP-505",  0,  1, True),
    ("AP-301-Exec",      "Exec Suite",     "Floor 3", "AP-635", 20, 34, False),
    ("AP-302-OpenPlan",  "Open Office",    "Floor 3", "AP-515", 33, 42, False),
    ("AP-303-Boardroom", "Boardroom",      "Floor 3", "AP-635", 25, 36, False),
    ("AP-304-Kitchen",   "Kitchen",        "Floor 3", "AP-505", 10, 24, False),
    ("AP-305-Balcony",   "Balcony",        "Floor 3", "AP-505",  8, 20, False),
    ("AP-401-Support",   "Support",        "Floor 4", "AP-515", 26, 38, False),
    ("AP-402-Sales",     "Sales Floor",    "Floor 4", "AP-515", 38, 44, False),
    ("AP-403-Training",  "Training Rm",    "Floor 4", "AP-635", 30, 40, False),
    ("AP-404-Store",     "Storage",        "Floor 4", "AP-505",  0,  1, True),
    ("AP-G01-CarPark",   "Car Park",       "Ground",  "AP-505",  6, 18, False),
    ("AP-G02-Gym",       "Gym",            "Ground",  "AP-515", 14, 28, False),
    ("AP-G03-Cafe",      "Cafe",           "Ground",  "AP-515", 20, 32, False),
    ("AP-G04-Lobby2",    "South Lobby",    "Ground",  "AP-515", 24, 36, False),
    ("AP-G05-Security",  "Security Desk",  "Ground",  "AP-505",  5, 16, False),
]

# Typical office activity across the day (index = hour 0-23).
_HOURLY = (
    0.08, 0.06, 0.05, 0.05, 0.06, 0.10, 0.20, 0.45, 0.70, 0.90, 1.00, 1.00,
    0.85, 0.95, 1.00, 0.98, 0.90, 0.62, 0.36, 0.22, 0.16, 0.12, 0.10, 0.09,
)

_VENDOR_OS = [
    ("Apple", "macOS 14"), ("Apple", "iOS 17"), ("Apple", "iPadOS 17"),
    ("Dell", "Windows 11"), ("Lenovo", "Windows 11"), ("Lenovo", "Ubuntu 22.04"),
    ("HP", "Windows 11"), ("Microsoft", "Windows 11"), ("Samsung", "Android 14"),
    ("Google", "Android 14"), ("Google", "ChromeOS"), ("Intel", "Windows 11"),
]
_IOT_VENDOR_OS = [
    ("Espressif", "RTOS"), ("Raspberry Pi", "Raspbian"),
    ("Axis", "Camera FW"), ("Honeywell", "Sensor FW"),
]
_FIRST = ["amelia", "noah", "olivia", "liam", "ava", "ethan", "sofia", "james",
          "mia", "lucas", "isla", "leo", "grace", "max", "ruby", "adam",
          "chloe", "omar", "nina", "raj", "sara", "tom", "yara", "zack"]
_LAST = ["patel", "khan", "smith", "jones", "brown", "wilson", "evans", "clark",
         "singh", "murphy", "reed", "gray", "hughes", "cole", "diaz", "boyd"]
_ROLES = (["employee"] * 12) + (["guest"] * 3) + ["contractor", "iot", "admin"]


def _rand(seed):
    return random.Random(seed)


def _build_client_pool(n=260):
    """A stable roster of devices (same MAC/hostname each run)."""
    rng = _rand("netwatch-client-pool")
    pool = []
    for i in range(n):
        role = rng.choice(_ROLES)
        if role == "iot":
            vendor, os_ = rng.choice(_IOT_VENDOR_OS)
            hostname = f"iot-{vendor.lower().replace(' ', '')}-{1000 + i}"
            username = ""
        else:
            vendor, os_ = rng.choice(_VENDOR_OS)
            if role == "guest":
                username = f"guest-{rng.randint(1000, 9999)}"
                hostname = f"guest-device-{i}"
            else:
                username = f"{rng.choice(_FIRST)}.{rng.choice(_LAST)}"
                short = username.split('.')[0]
                kind = "macbook" if vendor == "Apple" and "mac" in os_ else \
                       ("iphone" if os_.startswith("iOS") else
                        ("android" if os_.startswith("Android") else "laptop"))
                hostname = f"{short}-{kind}-{i:03d}"
        mac = ":".join(f"{rng.randint(0, 255):02X}" for _ in range(6))
        pool.append({
            "mac": mac,
            "hostname": hostname,
            "username": username,
            "access_role": role,
            "vendor": vendor,
            "model_os": os_,
        })
    return pool


CLIENT_POOL = _build_client_pool()


def _factor(when: datetime) -> float:
    """Blend the current and next hour so the day-curve is smooth."""
    lo = _HOURLY[when.hour]
    hi = _HOURLY[(when.hour + 1) % 24]
    frac = when.minute / 60.0
    return lo + (hi - lo) * frac


def snapshot(when: datetime | None = None):
    """Return (access_points, clients) for a moment in time."""
    when = when or datetime.now()
    ts_seed = int(when.replace(second=0, microsecond=0).timestamp())
    rng = _rand(ts_seed)
    factor = _factor(when)

    access_points = []
    clients = []
    pool_index = 0

    for idx, (name, loc, floor, model, peak, cap, offline) in enumerate(_ROSTER):
        if offline:
            access_points.append({
                "name": name, "location": loc, "floor": floor, "model": model,
                "status": "Offline", "clients": 0, "load_pct": 0,
                "uptime_secs": 0,
            })
            continue

        jitter = rng.uniform(0.82, 1.12)
        count = max(0, round(peak * factor * jitter))
        count = min(count, cap)
        load = min(100, round(100 * count / cap)) if cap else 0
        # A stable-ish uptime that grows with wall-clock time.
        boot = when - timedelta(days=(idx % 12) + 1, hours=idx, minutes=idx * 3)
        uptime = int((when - boot).total_seconds())

        access_points.append({
            "name": name, "location": loc, "floor": floor, "model": model,
            "status": "Online", "clients": count, "load_pct": load,
            "uptime_secs": uptime,
        })

        # Assign `count` devices from the pool to this AP for this snapshot.
        for _ in range(count):
            dev = CLIENT_POOL[pool_index % len(CLIENT_POOL)]
            pool_index += 1
            octet_c = 10 + idx
            octet_d = rng.randint(2, 254)
            clients.append({
                **dev,
                "ip": f"10.{octet_c}.{floor_num(floor)}.{octet_d}",
                "status": "Connected",
                "ap_name": name,
            })

    return access_points, clients


def floor_num(floor: str) -> int:
    digits = "".join(ch for ch in floor if ch.isdigit())
    return int(digits) if digits else 0


class MockArubaClient:
    """Same interface as LiveArubaClient."""
    source = SOURCE

    def collect(self):
        """Return (access_points, clients) for right now."""
        return snapshot(datetime.now())

    def test_connection(self):
        return True, "Mock data source — always available."
