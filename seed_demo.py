"""
Seed the database with ~24 hours of realistic history from the mock source, so
every page (Status, Analytics, Client Log, Poll Log, Database) looks alive the
moment you open the app.

  python seed_demo.py

Safe to re-run: it clears the tables first for a clean slate.
"""
from datetime import datetime, timedelta

import db
from aruba import mock


def seed(hours=24, step_min=15, client_hours=8):
    db.init_db()
    now = datetime.now().replace(second=0, microsecond=0)
    start = now - timedelta(hours=hours)

    polls = 0
    with db.connection() as conn:
        conn.execute("DELETE FROM ap_log")
        conn.execute("DELETE FROM client_log")
        conn.execute("DELETE FROM poll_log")

        t = start
        while t <= now:
            ts = t.strftime("%Y-%m-%d %H:%M:%S")
            aps, clients = mock.snapshot(t)
            connected = sum(a["clients"] for a in aps)

            db.insert_ap_snapshot(conn, aps, ts)
            # Keep per-client detail only for the recent window (keeps DB small
            # while still giving the Client Log real roaming history to search).
            if t >= now - timedelta(hours=client_hours):
                db.insert_client_snapshot(conn, clients, ts)
            db.record_poll(conn, "mock", len(aps), connected, 5, True, "seeded", ts)

            polls += 1
            t += timedelta(minutes=step_min)

    print(f"Seeded {polls} polls from {start:%Y-%m-%d %H:%M} to {now:%H:%M} "
          f"({hours}h history, client detail for last {client_hours}h).")


if __name__ == "__main__":
    seed()
