def ap_summary(name: str, count: int) -> str:
    """Return a summary of an access point's client count."""
    return f"AP {name} has {count} clients"

print(ap_summary("Library-North", 23))

def client_summary(hostname, ip):
    return f"Host {hostname} is connected from {ip}"
print(client_summary("Laptop-42", "10.0.0.5"))


def make_label(count):
    return f"{count} clients"
def show_label(count):
    print(make_label(count))

x = make_label(5)
y = show_label(5)
print("x is:", x)
print("y is", y)


def poll(interval=300):
    return f"every {interval} seconds"

print(poll())
print(poll(90))
print(poll(interval=600))

client_count = 0

def record_client(name):
    global client_count
    client_count += 1
    print(f"{name} connected. Total: {client_count}")







