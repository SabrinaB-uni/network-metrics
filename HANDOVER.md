Wireless Monitoring Dashboard

Connects to Aruba Central, collects access-point and client status every few minutes, stores the
history in a SQLite database, and shows it on a login-protected web dashboard.

Runs at http://172.19.29.162:5000 · start with `python app.py` · login password is in `.env`.

 Features
 AP status: online/offline, clients, load, uptime (search + CSV export)
 Client log: search a device and trace which APs it used 
 Usage analytics: clients over the day, busiest APs 
 Poll history + database view 
 Aruba Central API integration (OAuth) 
 TLS checker: validates the cloud endpoints' certificates 
 Rogue-AP detection: flags APs not in the trusted baseline 
 Anomaly alerts : offline / rogue / spikes / out-of-hours  
 Login — session-based sign-in 
