"""
SQLite data layer for NetWatch.

Three tables:
  ap_log      — one row per access point per poll (history of AP state)
  client_log  — one row per client per poll (history of who was connected)
  poll_log    — one row per poll run (audit trail for the Poll Log page)

Everything the web app reads goes through the query helpers at the bottom,
so the routes never write raw SQL.
"""
import os
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS ap_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ap_name       TEXT    NOT NULL,
    location      TEXT,
    floor         TEXT,
    status        TEXT    NOT NULL,          -- 'Online' / 'Offline'
    total_clients INTEGER NOT NULL DEFAULT 0,
    load_pct      INTEGER NOT NULL DEFAULT 0,
    uptime_secs   INTEGER NOT NULL DEFAULT 0,
    model         TEXT,
    timestamp     TEXT    NOT NULL           -- 'YYYY-MM-DD HH:MM:SS'
);
CREATE INDEX IF NOT EXISTS idx_ap_log_ts   ON ap_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_ap_log_name ON ap_log(ap_name);

CREATE TABLE IF NOT EXISTS client_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip          TEXT,
    hostname    TEXT,
    mac         TEXT    NOT NULL,
    username    TEXT,
    access_role TEXT,
    vendor      TEXT,
    model_os    TEXT,
    status      TEXT    NOT NULL,            -- 'Connected' / 'Disconnected'
    ap_name     TEXT,
    timestamp   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_client_log_ts  ON client_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_client_log_mac ON client_log(mac);

CREATE TABLE IF NOT EXISTS poll_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,
    source       TEXT    NOT NULL,           -- 'mock' / 'live'
    ap_count     INTEGER,
    client_count INTEGER,
    duration_ms  INTEGER,
    success      INTEGER NOT NULL DEFAULT 1,  -- 1 = ok, 0 = failed
    message      TEXT
);
CREATE INDEX IF NOT EXISTS idx_poll_log_ts ON poll_log(timestamp);
"""


def get_conn():
    """Open a connection with dict-like rows."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables/indexes if they don't exist yet."""
    with connection() as conn:
        conn.executescript(SCHEMA)


# --------------------------------------------------------------------------
# Writes (used by the poller and the seed script)
# --------------------------------------------------------------------------
def insert_ap_snapshot(conn, aps, ts):
    rows = [
        {
            "ap_name": ap["name"],
            "location": ap.get("location"),
            "floor": ap.get("floor"),
            "status": ap["status"],
            "total_clients": ap.get("clients", 0),
            "load_pct": ap.get("load_pct", 0),
            "uptime_secs": ap.get("uptime_secs", 0),
            "model": ap.get("model"),
            "timestamp": ts,
        }
        for ap in aps
    ]
    conn.executemany(
        """INSERT INTO ap_log
             (ap_name, location, floor, status, total_clients,
              load_pct, uptime_secs, model, timestamp)
           VALUES (:ap_name, :location, :floor, :status, :total_clients,
                   :load_pct, :uptime_secs, :model, :timestamp)""",
        rows,
    )


def insert_client_snapshot(conn, clients, ts):
    rows = [
        {
            "ip": c.get("ip"),
            "hostname": c.get("hostname"),
            "mac": c["mac"],
            "username": c.get("username"),
            "access_role": c.get("access_role"),
            "vendor": c.get("vendor"),
            "model_os": c.get("model_os"),
            "status": c.get("status", "Connected"),
            "ap_name": c.get("ap_name"),
            "timestamp": ts,
        }
        for c in clients
    ]
    conn.executemany(
        """INSERT INTO client_log
             (ip, hostname, mac, username, access_role,
              vendor, model_os, status, ap_name, timestamp)
           VALUES (:ip, :hostname, :mac, :username, :access_role,
                   :vendor, :model_os, :status, :ap_name, :timestamp)""",
        rows,
    )


def record_poll(conn, source, ap_count, client_count, duration_ms, success, message, ts):
    conn.execute(
        """INSERT INTO poll_log
             (timestamp, source, ap_count, client_count, duration_ms, success, message)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ts, source, ap_count, client_count, duration_ms, 1 if success else 0, message),
    )


# --------------------------------------------------------------------------
# Reads (used by the web app)
# --------------------------------------------------------------------------
def latest_snapshot_ts():
    with connection() as conn:
        row = conn.execute("SELECT MAX(timestamp) AS ts FROM ap_log").fetchone()
        return row["ts"] if row else None


def latest_aps():
    """Most recent row per access point — i.e. the current status table."""
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT a.*
              FROM ap_log a
              JOIN (SELECT ap_name, MAX(timestamp) AS mts
                      FROM ap_log GROUP BY ap_name) latest
                ON a.ap_name = latest.ap_name AND a.timestamp = latest.mts
             ORDER BY a.ap_name
            """
        ).fetchall()
        return [dict(r) for r in rows]


def kpis():
    aps = latest_aps()
    total = len(aps)
    online = sum(1 for a in aps if a["status"] == "Online")
    offline = total - online
    active_clients = sum(a["total_clients"] for a in aps if a["status"] == "Online")
    availability = round(100 * online / total, 1) if total else 0.0
    return {
        "total": total,
        "online": online,
        "offline": offline,
        "active_clients": active_clients,
        "availability": availability,
    }


def clients_timeseries():
    """Total connected clients per poll for the most recent day of data."""
    with connection() as conn:
        day = conn.execute("SELECT MAX(date(timestamp)) AS d FROM poll_log").fetchone()["d"]
        if not day:
            return []
        rows = conn.execute(
            """SELECT timestamp, client_count
                 FROM poll_log
                WHERE date(timestamp) = ? AND success = 1
                ORDER BY timestamp""",
            (day,),
        ).fetchall()
        return [{"t": r["timestamp"], "clients": r["client_count"] or 0} for r in rows]


def ap_popularity():
    """Average/peak clients per AP over the most recent day (busiest first)."""
    with connection() as conn:
        day = conn.execute("SELECT MAX(date(timestamp)) AS d FROM ap_log").fetchone()["d"]
        if not day:
            return []
        rows = conn.execute(
            """SELECT ap_name, location,
                      AVG(total_clients) AS avg_c,
                      MAX(total_clients) AS max_c
                 FROM ap_log
                WHERE date(timestamp) = ?
                GROUP BY ap_name
                ORDER BY avg_c DESC""",
            (day,),
        ).fetchall()
        return [
            {
                "ap_name": r["ap_name"],
                "location": r["location"],
                "avg_c": round(r["avg_c"], 1),
                "max_c": r["max_c"],
            }
            for r in rows
        ]


def status_breakdown_over_day():
    """Online vs offline AP counts per poll for the most recent day."""
    with connection() as conn:
        day = conn.execute("SELECT MAX(date(timestamp)) AS d FROM ap_log").fetchone()["d"]
        if not day:
            return []
        rows = conn.execute(
            """SELECT timestamp,
                      SUM(CASE WHEN status='Online'  THEN 1 ELSE 0 END) AS online,
                      SUM(CASE WHEN status='Offline' THEN 1 ELSE 0 END) AS offline
                 FROM ap_log
                WHERE date(timestamp) = ?
                GROUP BY timestamp
                ORDER BY timestamp""",
            (day,),
        ).fetchall()
        return [dict(r) for r in rows]


def search_clients(query=""):
    """Latest state per client (MAC), optionally filtered by a search term."""
    like = f"%{query.strip()}%"
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*
              FROM client_log c
              JOIN (SELECT mac, MAX(timestamp) AS mts
                      FROM client_log GROUP BY mac) latest
                ON c.mac = latest.mac AND c.timestamp = latest.mts
             WHERE (? = '' )
                OR c.hostname LIKE ? OR c.mac LIKE ? OR c.ip LIKE ?
                OR c.username LIKE ? OR c.ap_name LIKE ?
             ORDER BY c.hostname
             LIMIT 500
            """,
            (query.strip(), like, like, like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]


def client_ap_history(mac, limit=50):
    """Which APs a given device has connected to, most recent first."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT ap_name, status, timestamp
                 FROM client_log
                WHERE mac = ?
                ORDER BY timestamp DESC
                LIMIT ?""",
            (mac, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def recent_poll_log(limit=100):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM poll_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def db_overview():
    tables = ["ap_log", "client_log", "poll_log"]
    out = {"tables": [], "path": config.DB_PATH, "size_bytes": 0}
    if os.path.exists(config.DB_PATH):
        out["size_bytes"] = os.path.getsize(config.DB_PATH)
    with connection() as conn:
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            rng = conn.execute(
                f"SELECT MIN(timestamp) AS lo, MAX(timestamp) AS hi FROM {t}"
            ).fetchone()
            out["tables"].append(
                {"name": t, "rows": count, "first": rng["lo"], "last": rng["hi"]}
            )
    return out


def recent_rows(table, limit=25):
    """A small preview of the newest rows in a table (read-only)."""
    if table not in ("ap_log", "client_log", "poll_log"):
        return [], []
    with connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        rows = [dict(r) for r in rows]
    columns = list(rows[0].keys()) if rows else []
    return columns, rows
