import csv
import io
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, Response

import config
import db
import charts
from aruba.client import get_client

app = Flask(__name__)
db.init_db()

NAV = [
    ("Monitoring", [
        ("ap_status", "AP Status", "▦"),
        ("analytics", "Analytics", "◍"),
        ("client_log", "Client Log", "◉"),
    ]),
    ("System", [
        ("api_config", "API Config", "⚙"),
        ("poll_log", "Poll Log", "≣"),
    ]),
    ("Data", [
        ("database", "Database", "◫"),
    ]),
]


@app.template_filter("uptime")
def format_uptime(secs):
    secs = int(secs or 0)
    if secs <= 0:
        return "—"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    return f"{days}d {hours}h" if days else f"{hours}h {mins}m"


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
        high = a["load_pct"] >= 85
        a["alert"] = a["status"] == "Offline" or high
        a["load_class"] = "high" if high else ("warn" if a["load_pct"] >= 60 else "ok")
    return aps


@app.context_processor
def inject_globals():
    k = db.kpis()
    failed = sum(1 for p in db.recent_poll_log(120) if not p["success"])
    return {
        "APP_NAME": config.APP_NAME,
        "APP_TAGLINE": config.APP_TAGLINE,
        "data_source": config.data_source_label(),
        "use_mock": config.USE_MOCK,
        "poll_interval": config.POLL_INTERVAL,
        "net_health": k["availability"],
        "last_polled": db.latest_snapshot_ts(),
        "nav": NAV,
        "badges": {"ap_status": k["offline"] or None, "poll_log": failed or None, "database": "OK"},
        "server_time": datetime.now().strftime("%H:%M:%S"),
    }


@app.route("/")
def ap_status():
    q = request.args.get("q", "").strip()
    flt = request.args.get("filter", "all")
    aps = _annotate(db.latest_aps())

    if q:
        ql = q.lower()
        aps = [a for a in aps if ql in (a["ap_name"] or "").lower()
               or ql in (a["location"] or "").lower()]
    if flt == "online":
        aps = [a for a in aps if a["status"] == "Online"]
    elif flt == "offline":
        aps = [a for a in aps if a["status"] == "Offline"]
    elif flt == "alerts":
        aps = [a for a in aps if a["alert"]]

    return render_template("ap_status.html", active="ap_status",
                           aps=aps, kpi=db.kpis(), q=q, flt=flt)


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
        "access_token_set": bool(config.ARUBA_ACCESS_TOKEN),
        "refresh_token_set": bool(config.ARUBA_REFRESH_TOKEN),
    }
    return render_template("api_config.html", active="api_config", cfg=cfg, test=test)


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


@app.route("/refresh", methods=["POST"])
def refresh():
    from poller import poll_once
    poll_once()
    return redirect(request.referrer or url_for("ap_status"))


if __name__ == "__main__":
    app.run(debug=True)
