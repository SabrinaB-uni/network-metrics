# network-metrics — Progress & Resume Notes

> **Purpose of this file:** it travels *with the code*, so on any machine (Windows work PC or Mac
> at home) you can open this project, read this file, and pick up exactly where you left off.
> To resume with Claude: `cd` into this folder and say *"Read PROGRESS.md and continue from where I am."*

## What this project is
An **Aruba wireless monitoring + alerting** app (Flask + SQLite). It polls the HPE Aruba
Networking Central API on an interval, logs access points and clients to a SQLite database, and
serves a dark "command-centre" dashboard. Security features are core, not extras: a **TLS checker**
and an **anomaly-detection + alerting layer** (email/Slack). Built as a learning project and a
portfolio piece for a postgraduate **security** role. Deadline target: **Sun 2026-08-16**.

## Stack
- Python 3.13, Flask 3.0.3
- SQLite (via built-in `sqlite3`), browsed in HeidiSQL
- `requests` (added in Module 3)

## Setup on a new machine
```bash
# 1) create the virtual environment (do NOT copy venv/ between machines)
python -m venv venv          # macOS: python3 -m venv venv

# 2) activate it
.\venv\Scripts\Activate.ps1  # Windows PowerShell
source venv/bin/activate      # macOS / Linux

# 3) install dependencies
pip install -r requirements.txt

# 4) run a practice file
python main.py             # macOS: python3 main.py
```

## Curriculum (modules)
0. Foundations & setup ✅
1. Functions
2. Dictionaries & lists
3. APIs (incl. mock Aruba client; 3.7 = real `aruba_live.py`)
4. SQL & SQLite (the AP log + Client log tables)
5. The Poller
6. Debugging & robustness
7. TLS checker (transport security)  🔐
8. Anomaly detection & alerting (incl. 8.7 email/Slack notifications)  🔐
9. Flask web app (Status page, Client search, AP graph, TLS panel, Alerts panel)
10. Deployment & polish (`waitress`, Task Scheduler, `USE_MOCK=false` cutover)

## Timetable (3 weeks, weekdays = work, weekends = catch-up)
- **Week 1 (27–31 Jul):** Modules 1–4 pt.1 (functions → dicts → APIs → start SQL)
- **Week 2 (3–7 Aug):** SQL pt.2 → Poller → Debugging → TLS checker
- **Week 3 (10–14 Aug):** Anomaly & alerting → Flask dashboard → polish
- Deadline + write-up: **Sun 16 Aug**

## CURRENT STATUS  📍
- **Done:** Lessons 1.1, 1.1b, 1.2, 1.3 (functions, parameters, return vs print, default/keyword args).
- **Next up:** **Exercise 1.4** — add type hints + a docstring to `ap_summary`.
- Practice code lives in `scratch.py`; the Flask app is in `app.py` (leave app.py clean).

## Key concepts locked in so far
- A function takes **parameters** (inputs) and hands back a value with **`return`**. Don't reassign
  parameters inside — use them.
- **`print` talks to a human; `return` talks to the rest of the program.** A function with no
  `return` gives back `None`.
- **Default arguments**: `def poll(interval=300):` — call as `poll()`, `poll(60)`, or `poll(interval=900)`.
- **f-strings only substitute what's inside `{ }`**: `f"every {interval} s"` ✅ vs `f"every interval s"` ❌.

## Teaching style (for Claude)
Mentor cadence: one concept, then an exercise, then wait for the attempt before showing the answer.
Mix "write from scratch" (fluency) with "predict then run" (understanding).
