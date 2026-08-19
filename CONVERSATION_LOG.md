# network-metrics — Full Mentoring Log (Lessons 1.1 – 1.4)

> A complete record of the session that built this project — **your prompts + every lesson, with
> code and exercises** — so you can pick it all up on any machine. Pairs with `PROGRESS.md`
> (which holds the curriculum, timetable, and "where you are"). To continue with Claude on a new
> machine: `cd` into this project and say *"Read PROGRESS.md and CONVERSATION_LOG.md and continue."*

---

## Project & decisions (the context)

- **What:** Aruba wireless monitoring + alerting app. Flask + SQLite. Polls the HPE Aruba
  Networking Central API, logs Access Points + Clients to SQLite, serves a dark "command-centre"
  dashboard (Status page, AP client-count graph, client search).
- **Security features (core, not extras):** a **TLS checker** and an **anomaly-detection +
  alerting layer** (email/Slack) — to strengthen a postgraduate security-role application.
- **Database:** SQLite (built-in `sqlite3`), browsed in HeidiSQL.
- **Teaching contract:** one concept → an exercise → you attempt it → *then* the model answer.
- **Timeline:** originally 3 weeks (target 16 Aug); may compress to ~2 weeks — ask Claude to
  re-flow the timetable if so.

### Key architecture idea
```
Aruba API  →(poll)→  SQLite DB  →(read)→  Flask web app (browser)
   ▲ Poller           ▲ meeting point        ▲ Status / Graph / Search
```
The poller and the website **never talk directly** — the database is the meeting point.

### Deployment notes (from the "deploy for the company" discussion)
- Build against a **mock Aruba client** (`aruba_mock.py`) first — safe, offline.
- For production, a **real** client (`aruba_live.py`) with the same function names/return shape.
- Flip between them with one setting: `USE_MOCK=false` in `.env`.
- Only ever call **read-only monitoring (GET)** endpoints. Get **authorization** + API creds from
  the company. Serve with `waitress` + Task Scheduler (not the Flask dev server).

---

## Module 1 — Functions

### Lesson 1 — Setup & the big picture
**You asked:** to build the Aruba app in Flask + Python + HeidiSQL, taught in beginner lessons.
- Created a virtual environment (`venv`), installed Flask, made `app.py` with two routes.
- **A route = URL + function:** `@app.route("/")` runs the function under it and returns HTML.
- `app = Flask(__name__)` is the application object; `debug=True` auto-reloads on save.

### Lesson 1.1 — Functions: parameters & `return`
**You asked:** "Act as a senior Python mentor… teach through the Aruba project."
- A **function** takes inputs (**parameters**) and hands back an output (**`return`**).
- **Your first attempt** had three classic traps:
  1. **Overwrote the parameters** (`name = "Library-North"` inside) — ignore the inputs = not a real function.
  2. **String + int crash:** `"..." + 23` → `TypeError`. Use an f-string (auto-converts) or `str(23)`.
  3. **Used `print` instead of `return`.**
- **Model answer:**
```python
def ap_summary(name, count):
    return f"AP {name} has {count} clients"

print(ap_summary("Library-North", 23))   # AP Library-North has 23 clients
```
- **Mental model:** parameters are empty boxes the caller fills; *use* them, don't refill them.

### Exercise 1.1b — `client_summary`
- **Your attempt** bugs: `10.0.0.5` without quotes = **SyntaxError** (an IP is text → quotes);
  and `print(...)` was **inside** the function *after* `return` (unreachable dead code).
- **Model answer:**
```python
def client_summary(hostname, ip):
    return f"Host {hostname} is connected from {ip}"

print(client_summary("laptop-42", "10.0.0.5"))
```

### Lesson 1.2 — `return` vs `print` (and `None`)
**You asked:** "why give me the code instead of making me write it? is predicting better?"
- **Answer:** technique matches the goal. *Write-from-scratch* builds fluency; *predict-then-run*
  (the **PRIMM** method) builds a mental model and mirrors debugging. 1.2 used prediction on purpose.
- **The concept:** `print` talks to a human and returns `None`; `return` hands a value back to your
  program. A function with no `return` gives back `None`.
```python
def make_label(count):
    return f"{count} clients"   # x catches this value

def show_label(count):
    print(f"{count} clients")   # prints, returns None

x = make_label(5)   # x == "5 clients"
y = show_label(5)    # prints "5 clients", y == None
```
- **Why it matters:** the poller inserts *returned* values into SQLite; Flask puts *returned* values
  on the page. A printout can't be caught by either. **Returning is how data flows through the app.**

### Lesson 1.3 — Default & keyword arguments
**You asked** (jumped ahead): `poll (interval-300)`
- Bugs: `-` means *subtract*; `=` means *bind a value* → use `interval=300`. And a default lives in
  the **`def` line's own parentheses** — you don't `def interval:` separately; a parameter is an
  automatic variable born inside the function.
- Then the body must be **indented**, and f-strings only substitute inside `{ }`:
  `f"...interval..."` prints the literal word; `f"...{interval}..."` substitutes the value.
- **Model answer:**
```python
def poll(interval=300):
    return f"Polling every {interval} seconds"

print(poll())              # Polling every 300 seconds   (default)
print(poll(60))            # Polling every 60 seconds     (positional)
print(poll(interval=900))  # Polling every 900 seconds    (keyword)
```

### Lesson 1.4 — Docstrings & type hints  ← **YOU ARE HERE**
- **Type hints** label inputs/output; not enforced at runtime, but your editor + tools use them:
```python
def poll(interval: int = 300) -> str:
    """Return a message describing the poll interval in seconds."""
    return f"Polling every {interval} seconds"
```
  `interval: int` = expects an int; `-> str` = returns a str; the `"""..."""` = docstring.
- **Exercise 1.4 (your next task):** add type hints + a one-line docstring to `ap_summary`.
  (What type is `name`? what type is `count`? what does it return?)

---

## Side topics covered
- **"Is health-monitoring + alerting included?"** → Yes, it *is* the project: poller (Module 5) +
  anomaly/alerting (Module 8). Email/Slack delivery = a small Module 8.7 (`smtplib` / a Slack webhook).
- **Cross-machine work** → Claude Code chats are stored **locally per machine** and don't sync;
  git + `PROGRESS.md` carry the *code and context* instead. claude.ai *website/app* chats do sync.

---

## Your current `scratch.py` (clean save-point)
```python
"""
main.py — practice pad. Run with: python main.py
"""

def ap_summary(name, count):
    return f"AP {name} has {count} clients"

def client_summary(hostname, ip):
    return f"Host {hostname} is connected from {ip}"

print(ap_summary("Library-North", 23))
print(client_summary("laptop-42", "10.0.0.5"))

def make_label(count):
    return f"{count} clients"

def show_label(count):
    print(f"{count} clients")

x = make_label(5)
y = show_label(5)
print("x is:", x)
print("y is:", y)

def poll(interval=300):
    return f"Polling every {interval} seconds"   # braces fixed

print(poll())
print(poll(90))
print(poll(interval=600))
```

## ▶️ Resume point
**Exercise 1.4** — add type hints + a docstring to `ap_summary`, run it, and share your attempt.
Then: 1.5 (pure functions) closes Module 1, and Module 2 begins dictionaries.
