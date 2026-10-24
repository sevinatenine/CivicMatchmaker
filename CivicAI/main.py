import os


def load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    """KEY=value lines from CivicAI/.env (gitignored). Real env vars win over the file."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()  # before importing server, so ai.py sees the vars at import time

from server import run_server  # noqa: E402

run_server()
