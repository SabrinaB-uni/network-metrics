"""Anomaly detection: scans the latest data for problems, logs alerts, and can push them to Slack."""
import statistics
from datetime import datetime

import requests

import config
import db

# Working hours — connections outside this window are worth flagging.
WORK_START, WORK_END = 7, 19


def run_detection():
    """Check the latest data for anomalies, log new alerts, and notify. Returns the new alerts."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    aps = db.latest_aps()
    known = db.get_known_aps()
    new = []

    def raise_alert(severity, rule, entity, detail):
        if not db.alert_exists_recent(rule, entity, 60):
            db.add_alert(ts, severity, rule, entity, detail)
            new.append({"severity": severity, "rule": rule, "entity": entity, "detail": detail})

    for a in aps:
        if a["status"] == "Offline":
            raise_alert("warning", "ap_offline", a["ap_name"], f"{a['location']} is offline")
        elif a["load_pct"] >= 85:
            raise_alert("warning", "high_load", a["ap_name"], f"load {a['load_pct']}%")
        if known and a["ap_name"] not in known:
            raise_alert("critical", "rogue_ap", a["ap_name"], "unrecognised access point")

    hour = datetime.now().hour
    if hour < WORK_START or hour >= WORK_END:
        active = sum(a["total_clients"] for a in aps if a["status"] == "Online")
        if active > 20:
            raise_alert("warning", "off_hours", "network", f"{active} clients connected out of hours")

    series = [p["clients"] for p in db.clients_timeseries()]
    if len(series) >= 6:
        history, latest = series[:-1][-12:], series[-1]
        mean, sd = statistics.mean(history), statistics.pstdev(history)
        if sd > 0 and latest > mean + 2 * sd and latest > mean + 10:
            raise_alert("warning", "client_spike", "network",
                        f"{latest} clients vs typical {mean:.0f}")

    for alert in new:
        notify(alert)
    return new


def notify(alert):
    if not config.SLACK_WEBHOOK_URL:
        return
    text = f"[{alert['severity'].upper()}] {alert['rule']} — {alert['entity']}: {alert['detail']}"
    try:
        requests.post(config.SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except requests.RequestException:
        pass
