"""
All server settings, in one place.

Values come from the repo-root .env file (gitignored; copy .env.example to start).
Real environment variables win over the file, which is how Docker / Render pass them in.
Every other module reads settings from here instead of os.environ.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_env(path):
    """KEY=value lines. Existing environment variables are never overwritten."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.split(" #", 1)[0].strip()   # allow "KEY=value  # comment"
            os.environ.setdefault(key.strip(), value.strip("'\""))


load_env(os.path.join(ROOT, ".env"))


def _get(key, default=None):
    return os.environ.get(key) or default


def _path(key, default):
    p = _get(key, default)
    return p if os.path.isabs(p) else os.path.join(HERE, p)


# local  = server on this machine, Julia 1 running in-process
# hosted = server on Render, decisions through OpenRouter
APP_ENV = _get("APP_ENV", "local")

# Which decision model answers the classification questions: "julia" or "openrouter".
# Follows APP_ENV unless set explicitly.
LLM_PROVIDER = _get("LLM_PROVIDER", "openrouter" if APP_ENV == "hosted" else "julia")

JULIA_MODEL_DIR = _path("JULIA_MODEL_DIR", "Julia-1")
JULIA_DEVICE = _get("JULIA_DEVICE", "cpu")

OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "microsoft/microsoft-decision-1")
OPENROUTER_URL = _get("OPENROUTER_URL", "https://openrouter.ai/api/alpha/decisions")

GOOGLE_CIVIC_API_KEY = _get("GOOGLE_CIVIC_API_KEY")
CANDIDATES_DIR = _path("CANDIDATES_DIR", "scraped")

HOST = _get("HOST", "0.0.0.0")
PORT = int(_get("PORT", 4000))
MAX_CONCURRENT = int(_get("MAX_CONCURRENT", 2))
MAX_QUEUED = int(_get("MAX_QUEUED", 50))
DEBUG = _get("DEBUG") == "1" or _get("JULIA_DEBUG") == "1"   # print every pairing the model made
