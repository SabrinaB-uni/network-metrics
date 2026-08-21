"""Collect a snapshot from Aruba (mock or live) and write it to the database.

    python poller.py          poll forever on POLL_INTERVAL
    python poller.py --once    single poll, then exit
"""
import argparse
import logging
import time
from datetime import datetime

import config
import db
from aruba.client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [poller] %(message)s")
log = logging.getLogger("poller")


def poll_once(client=None):
    client = client or get_client()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    started = time.time()
    try:
        aps, clients = client.collect()
    except Exception as exc:
        with db.connection() as conn:
            db.record_poll(conn, client.source, 0, 0,
                           int((time.time() - started) * 1000), False, str(exc), ts)
        log.error("poll failed: %s", exc)
        return {"error": str(exc)}

    connected = sum(1 for c in clients if c.get("status") == "Connected")
    with db.connection() as conn:
        db.insert_ap_snapshot(conn, aps, ts)
        db.insert_client_snapshot(conn, clients, ts)
        db.record_poll(conn, client.source, len(aps), connected,
                       int((time.time() - started) * 1000), True, "ok", ts)
    log.info("polled %d APs / %d clients (%s)", len(aps), connected, client.source)
    return {"aps": len(aps), "clients": connected}


def run_forever(interval=None):
    interval = interval or config.POLL_INTERVAL
    db.init_db()
    client = get_client()
    log.info("starting poller: source=%s interval=%ss", client.source, interval)
    while True:
        poll_once(client)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetWatch poller")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    args = parser.parse_args()
    db.init_db()
    if args.once:
        poll_once()
    else:
        run_forever()
