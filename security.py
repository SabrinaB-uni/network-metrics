"""Security checks — a TLS/certificate inspector for the cloud endpoints the app talks to."""
import socket
import ssl
import time
from datetime import datetime, timezone


def check_tls(host, port=443):
    """Inspect a host's TLS certificate: validity, protocol, and expiry."""
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                proto = ssock.version()
    except Exception as exc:
        return {"host": host, "verdict": "FAIL", "reason": str(exc)}

    expires_epoch = ssl.cert_time_to_seconds(cert["notAfter"])
    days_left = int((expires_epoch - time.time()) / 86400)
    expires = datetime.fromtimestamp(expires_epoch, timezone.utc).strftime("%Y-%m-%d")
    issuer = dict(x[0] for x in cert.get("issuer", ())).get("organizationName", "")

    if days_left < 0:
        verdict, reason = "FAIL", "certificate expired"
    elif proto in ("SSLv3", "TLSv1", "TLSv1.1"):
        verdict, reason = "WARN", "weak protocol " + proto
    elif days_left < 21:
        verdict, reason = "WARN", "expires in %d days" % days_left
    else:
        verdict, reason = "OK", "valid"

    return {"host": host, "verdict": verdict, "reason": reason, "protocol": proto,
            "issuer": issuer, "expires": expires, "days_left": days_left}
