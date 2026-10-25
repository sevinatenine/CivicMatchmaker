"""
Usage counters that survive redeploys: app opens, completed matches ("decisions"), and how
many different IP addresses and devices have opened the app.

Render's free disk is wiped on every deploy and every sleep, so the counts live in Upstash
Redis (free tier), reached over its REST API. Set UPSTASH_REDIS_REST_URL and
UPSTASH_REDIS_REST_TOKEN; without them (local dev) the counts are kept in memory instead.

Unique IPs and devices go into HyperLogLogs (PFADD / PFCOUNT), which count distinct values
without storing them, and each value is hashed first, so no IP or device ID is ever stored.
"""

import hashlib
import json
import threading
import urllib.request

import config

TIMEOUT = 5
OPENS, DECISIONS, IPS, DEVICES = "stats:opens", "stats:decisions", "stats:ips", "stats:devices"

_lock = threading.Lock()
_memory = {OPENS: 0, DECISIONS: 0, IPS: set(), DEVICES: set()}   # used when Upstash isn't set


def _persistent():
    return bool(config.UPSTASH_REDIS_REST_URL and config.UPSTASH_REDIS_REST_TOKEN)


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _pipeline(commands):
    """Run Redis commands in one request; returns each command's result."""
    req = urllib.request.Request(
        config.UPSTASH_REDIS_REST_URL.rstrip("/") + "/pipeline",
        data=json.dumps(commands).encode(),
        headers={"Authorization": f"Bearer {config.UPSTASH_REDIS_REST_TOKEN}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return [item.get("result") for item in json.load(r)]


_READS = [["GET", OPENS], ["GET", DECISIONS], ["PFCOUNT", IPS], ["PFCOUNT", DEVICES]]


def _run(writes, memory_update):
    """Apply the writes, then read the counts, in one request. Stats never break the app:
    on any error this logs and returns zeros."""
    values = [0, 0, 0, 0]
    try:
        if _persistent():
            values = _pipeline(writes + _READS)[len(writes):]
        else:
            with _lock:
                memory_update()
                values = [_memory[OPENS], _memory[DECISIONS],
                          len(_memory[IPS]), len(_memory[DEVICES])]
    except Exception as e:  # noqa: BLE001
        print(f"Usage stats unavailable: {e}", flush=True)
    opens, decisions, ips, devices = (int(v or 0) for v in values)
    return {"opens": opens, "decisions": decisions, "unique_ips": ips,
            "unique_devices": devices, "persistent": _persistent()}


def record_open(ip, device):
    """One app launch, from this IP address and (if the app sent one) this device ID.
    Returns the counts."""
    writes = [["INCR", OPENS]]
    if ip:
        writes.append(["PFADD", IPS, _hash(ip)])
    if device:
        writes.append(["PFADD", DEVICES, _hash(device)])

    def update():
        _memory[OPENS] += 1
        if ip:
            _memory[IPS].add(_hash(ip))
        if device:
            _memory[DEVICES].add(_hash(device))

    return _run(writes, update)


def record_decision():
    """One completed match."""
    def update():
        _memory[DECISIONS] += 1

    _run([["INCR", DECISIONS]], update)


def counts():
    """{opens, decisions, unique_ips, unique_devices, persistent}"""
    return _run([], lambda: None)
