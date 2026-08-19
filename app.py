"""
network-metrics — Aruba wireless monitoring
Lesson 1: the smallest possible Flask web app.

Run it with:   python app.py
Then open:      http://127.0.0.1:5000
"""

# 1) Import the Flask class from the flask package we installed.
from flask import Flask

# 2) Create THE application object. __name__ tells Flask where it lives
#    (so it can find templates/static files later). You'll see "app" again
#    and again — it's the heart of every Flask program.
app = Flask(__name__)
'''Write ap_summary(name, count) that returns the string AP Library-North has 
23 clients, call it with ap_summary("Library-North", 23), print the result, and run it.
 Paste me your attempt + any output or error 
— broken is fine — and I'll critique it before showing a clean version.'''



# 3) A "route" connects a URL to a Python function.
#    The @app.route("/") line means: when someone visits the home page "/",
#    run the function directly below it and send back whatever it returns.
@app.route("/")
def home():
    return "<h1>network-metrics is alive</h1><p>Lesson 1 complete.</p>"


# 4) A second route, just to prove routing works. Visit /ping in the browser.
@app.route("/ping")
def ping():
    return "pong"
#Exercise 1.1b — cement it before we move on
#Same skill, new data, so the parameter idea sticks. Write:

#A function client_summary(hostname, ip)
#It returns (not prints) the string: Host laptop-42 is connected from 10.0.0.5
#Then print(client_summary("laptop-42", "10.0.0.5"))
#Rules to prove you got the lesson: don't reassign hostname or ip inside, and use an f-string. Run it, paste me the code + output. Once that's clean, Lesson 1.2 is return vs print properly — which your Trap 3 sets up perfectly.


def client_summary(hostname, ip):
    return f"Host {hostname} is connected from {ip}"

print(client_summary("laptop-42", "10.0.0.5"))



# 5) This block only runs when you launch the file directly
#    (python app.py), not when it's imported. debug=True auto-reloads
#    the server whenever you save a change — handy while learning.
if __name__ == "__main__":
    app.run(debug=True)
