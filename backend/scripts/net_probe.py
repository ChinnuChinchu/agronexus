"""Prints which external hosts this server can reach (the output appears in the logs)."""

import socket
import time

import httpx

HOSTS = [
    ("api.openweathermap.org", 443),
    ("api.data.gov.in", 443),
    ("data.gov.in", 443),
]

for host, port in HOSTS:
    started = time.time()
    try:
        with socket.create_connection((host, port), timeout=10):
            print(f"[probe] {host}:{port} reachable in {time.time() - started:.2f}s")
    except OSError as exc:
        print(f"[probe] {host}:{port} NOT reachable: {type(exc).__name__}: {exc}")

try:
    response = httpx.get("https://api.data.gov.in", timeout=15, follow_redirects=True)
    print(f"[probe] https://api.data.gov.in answered with HTTP {response.status_code}")
except httpx.HTTPError as exc:
    print(f"[probe] https://api.data.gov.in request failed: {type(exc).__name__}")