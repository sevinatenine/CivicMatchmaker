"""
Decision model backends. Both take the same Julia-style request and return the same answers:

    predict(state, {"key": {"type": "choice", "instructions": ..., "criteria": {label: text}}})
      -> {"key": {"choice": label, "probabilities": {label: p}, "max_probability": p}}

  julia       Supersonic Labs' Julia 1, loaded in-process from JULIA_MODEL_DIR (local mode)
  openrouter  a hosted decision model (Microsoft-Decision-1, Jev 1.14, ...) through
              OpenRouter's /api/alpha/decisions endpoint, which takes the same
              {state, questions} request (hosted mode)

Pick one with LLM_PROVIDER in .env. The classification prompts live in matcher.py and are
shared by both.
"""

import json
import threading
import time
import urllib.error
import urllib.request

import config

# ------------------------------------------------------------------ julia (local)
_engine = None
_engine_lock = threading.Lock()
_predict_lock = threading.Lock()   # server runs several workers; keep inference serial


def _julia_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            from julia import load_model  # provided by the Julia-1 repo
            _engine = load_model(
                config.JULIA_MODEL_DIR, device=config.JULIA_DEVICE, strict_encoding=True,
                max_length=8192, head_length=1024,
            )
        return _engine


def _julia_predict(state, questions):
    with _predict_lock:
        return _julia_engine().predict(state=state, questions=questions)["answers"]


# ------------------------------------------------------------------ openrouter (hosted)
OPENROUTER_TIMEOUT = 60
OPENROUTER_TRIES = 4
_RETRY_CODES = {408, 429, 500, 502, 503, 504, 524, 529}


def _openrouter_predict(state, questions):
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")
    body = json.dumps({"model": config.OPENROUTER_MODEL, "state": state,
                       "questions": questions}).encode()
    req = urllib.request.Request(config.OPENROUTER_URL, data=body, headers={
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "CivicMatchmaker",
    })
    for attempt in range(OPENROUTER_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as r:
                return json.load(r)["answers"]
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_CODES or attempt == OPENROUTER_TRIES - 1:
                try:
                    msg = json.load(e)["error"]["message"]
                except Exception:  # noqa: BLE001
                    msg = str(e.reason)
                raise RuntimeError(f"OpenRouter HTTP {e.code}: {msg}") from None
        except (TimeoutError, urllib.error.URLError, OSError):
            if attempt == OPENROUTER_TRIES - 1:
                raise
        time.sleep(2 ** attempt)


# ------------------------------------------------------------------ shared
_BACKENDS = {"julia": _julia_predict, "openrouter": _openrouter_predict}


def describe():
    if config.LLM_PROVIDER == "openrouter":
        return f"openrouter ({config.OPENROUTER_MODEL})"
    return "julia (Julia 1, local)"


def warmup():
    """Load the local model now so the first request isn't slow. No-op for OpenRouter."""
    if config.LLM_PROVIDER == "julia":
        _julia_engine()


def predict(state, questions):
    try:
        backend = _BACKENDS[config.LLM_PROVIDER]
    except KeyError:
        raise RuntimeError(f"Unknown LLM_PROVIDER {config.LLM_PROVIDER!r} "
                           f"(use one of: {', '.join(_BACKENDS)})") from None
    answers = backend(state, questions)
    # OpenRouter answers carry "confidence" instead of Julia's "max_probability"; the
    # thresholds in matcher.py compare against the chosen option's probability
    for a in answers.values():
        if "max_probability" not in a:
            probs = a.get("probabilities") or {}
            a["max_probability"] = max((float(p) for p in probs.values()), default=0.0)
    return answers
