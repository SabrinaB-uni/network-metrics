import csv
import hmac
import io
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, request, url_for, redirect, session, Response

import config
import db
import charts
import security
import anomalies
from aruba.client import get_client

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
db.init_db()

PUBLIC_ENDPOINTS = {"login", "static"}


@app.before_request
def require_login():
    if request.endpoint not in PUBLIC_ENDPOINTS and not session.get("authed"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if not config.DASHBOARD_PASSWORD:
        error = "Login is not set up — add DASHBOARD_PASSWORD to .env."
    elif request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), config.DASHBOARD_PASSWORD):
            session["authed"] = True
            return redirect(url_for("ap_status"))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


NAV = [
    ("ap_status", "AP status"),
    ("client_log", "Client log"),
    ("analytics", "AP analysis"),
    ("security_page", "Security"),
    ("poll_log", "Poll history"),
    ("api_config", "API config"),
    ("database", "Database"),
]


@app.template_filter("uptime")
def format_uptime(secs):
    secs = int(secs or 0)
    if secs <= 0:
        return "—"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    return f"{days}d {hours:02d}h" if days else f"{hours}h {mins:02d}m"


@app.template_filter("ago")
def time_ago(ts):
    if not ts:
        return "—"
    try:
        t = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts
    secs = int((datetime.now() - t).total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


@app.template_filter("clock")
def clock(ts):
    if not ts:
        return "—"
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
    except ValueError:
        return ts


@app.template_filter("bytes")
def fmt_bytes(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _annotate(aps):
    for a in aps:
        high = a["status"] == "Online" and a["load_pct"] >= 85
        a["load_class"] = "high" if high else ("warn" if a["load_pct"] >= 60 else "ok")
        a["high_load"] = high
    return aps


@app.context_processor
def inject_globals():
    return {
        "APP_NAME": config.APP_NAME,
        "APP_TAGLINE": config.APP_TAGLINE,
        "poll_interval": config.POLL_INTERVAL,
        "last_polled": db.latest_snapshot_ts(),
        "nav": NAV,
    }


@app.route("/")
def ap_status():
    q = request.args.get("q", "").strip()
    flt = request.args.get("status", "all")

    aps = _annotate(db.latest_aps())
    kpi = db.kpis()
    kpi["high_load"] = sum(1 for a in aps if a["high_load"])
    total = len(aps)

    if q:
        ql = q.lower()
        aps = [a for a in aps if ql in (a["ap_name"] or "").lower()
               or ql in (a["location"] or "").lower()]
    if flt == "online":
        aps = [a for a in aps if a["status"] == "Online"]
    elif flt == "offline":
        aps = [a for a in aps if a["status"] == "Offline"]
    elif flt == "high":
        aps = [a for a in aps if a["high_load"]]

    overview = db.db_overview()
    db_rows = sum(t["rows"] for t in overview["tables"])

    return render_template("ap_status.html", active="ap_status",
                           aps=aps, kpi=kpi, q=q, status=flt,
                           showing=len(aps), total=total, db_rows=db_rows)


@app.route("/analytics")
def analytics():
    ts = db.clients_timeseries()
    values = [p["clients"] for p in ts]
    labels = [clock(p["t"]) for p in ts]
    popularity = db.ap_popularity()

    line = charts.line_chart(values, labels)
    bars = charts.bar_chart(
        [{"label": p["ap_name"], "sub": p["location"], "value": int(round(p["avg_c"]))}
         for p in popularity[:15]]
    )
    stats = {
        "peak": max(values) if values else 0,
        "now": values[-1] if values else 0,
        "busiest": popularity[0]["ap_name"] if popularity else "—",
        "samples": len(values),
    }
    return render_template("analytics.html", active="analytics",
                           line=line, bars=bars, stats=stats)


@app.route("/clients")
def client_log():
    q = request.args.get("q", "").strip()
    mac = request.args.get("mac", "").strip()
    history = db.client_ap_history(mac) if mac else None
    return render_template("client_log.html", active="client_log",
                           clients=db.search_clients(q), q=q, mac=mac, history=history)


@app.route("/api-config")
def api_config():
    test = get_client().test_connection() if request.args.get("test") == "1" else None
    cfg = {
        "base_url": config.ARUBA_BASE_URL or "(not set)",
        "client_id_set": bool(config.ARUBA_CLIENT_ID),
        "client_secret_set": bool(config.ARUBA_CLIENT_SECRET),
    }
    return render_template("api_config.html", active="api_config", cfg=cfg, test=test)


@app.route("/security", methods=["GET", "POST"])
def security_page():
    if request.method == "POST" and request.form.get("action") == "baseline":
        names = [a["ap_name"] for a in db.latest_aps()]
        db.set_baseline_aps(names, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return redirect(url_for("security_page"))

    hosts = []
    if config.ARUBA_BASE_URL:
        hosts.append(urlparse(config.ARUBA_BASE_URL).hostname)
    hosts.append("sso.common.cloud.hpe.com")
    tls = [security.check_tls(h) for h in hosts if h]

    known = db.get_known_aps()
    aps = db.latest_aps()
    for a in aps:
        a["known"] = a["ap_name"] in known
    unknown = [a for a in aps if not a["known"]]

    anomalies.run_detection()
    return render_template("security.html", active="security_page",
                           tls=tls, aps=aps, known_count=len(known),
                           unknown=unknown, baselined=bool(known),
                           alerts=db.recent_alerts(30))


@app.route("/poll-log")
def poll_log():
    return render_template("poll_log.html", active="poll_log", polls=db.recent_poll_log(150))


@app.route("/database")
def database():
    table = request.args.get("table", "ap_log")
    columns, rows = db.recent_rows(table)
    return render_template("database.html", active="database",
                           overview=db.db_overview(), table=table,
                           columns=columns, rows=rows)


@app.route("/export/aps.csv")
def export_aps():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ap_name", "location", "floor", "status", "total_clients",
                     "load_pct", "uptime_secs", "model", "timestamp"])
    for a in db.latest_aps():
        writer.writerow([a["ap_name"], a["location"], a["floor"], a["status"],
                         a["total_clients"], a["load_pct"], a["uptime_secs"],
                         a["model"], a["timestamp"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=ap_status.csv"})


if __name__ == "__main__":
    import threading
    import poller
    # background poller: collects a snapshot on an interval so history builds itself
    threading.Thread(target=poller.run_forever, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
