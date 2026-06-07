import json
import os
import tempfile
import threading
import time

from config import RATE_LIMIT_MAX_RUNS, RATE_LIMIT_WINDOW_HOURS

_WINDOW = RATE_LIMIT_WINDOW_HOURS * 3600
_DATA_FILE = os.path.join(tempfile.gettempdir(), "pulsecheck_rate_limit.json")
_lock = threading.Lock()


def _load():
    try:
        with open(_DATA_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    with open(_DATA_FILE, "w") as f:
        json.dump(data, f)


def check(ip: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, runs_used, seconds_until_oldest_expires).
    Records the run if allowed.
    """
    now = time.time()
    cutoff = now - _WINDOW

    with _lock:
        data = _load()

        # Keep only timestamps within the rolling window
        timestamps = [t for t in data.get(ip, []) if t > cutoff]

        if len(timestamps) >= RATE_LIMIT_MAX_RUNS:
            reset_in = int(timestamps[0] + _WINDOW - now)
            return False, len(timestamps), max(reset_in, 0)

        timestamps.append(now)
        data[ip] = timestamps

        # Prune stale entries for all IPs to keep the file small
        data = {k: [t for t in v if t > cutoff] for k, v in data.items() if v}
        _save(data)

    return True, len(timestamps), 0
