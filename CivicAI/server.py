"""
Flask SSE task server.

POST /run  (JSON body)  ->  text/event-stream

Events sent back:
  queued   {"position": N}            waiting for a free worker
  started  {"id": "..."}              a worker picked it up
  progress {...}                      whatever your task emits
  result   {...}                      final result
  error    {"message": "..."}         task raised
  (stream then closes)

If the client disconnects at any point, the job is cancelled:
  - still queued  -> removed from the queue, never runs
  - already running -> its cancel_event is set; the task should check it

Also:
  GET /voting-places?address=&city=&state=&zip=   drop-off / early vote / polling places
  GET /status                                     queue size, decision model, candidates
  POST /visit  {"device": "<id>"}                 count an app launch; returns the usage counts
  GET /stats                                      usage counts (opens, decisions, IPs, devices)

Run:   python main.py
Test:  curl -N -X POST localhost:4000/run -H 'Content-Type: application/json' -d '{"steps": 8}'
       (Ctrl-C in curl to simulate a disconnect)

NOTE: state lives in memory, so run a SINGLE process. For production (the Docker image):
       gunicorn -w 1 -k gthread --threads 32 server:app
"""

import json
import threading
import time
import uuid
from collections import deque

from flask import Flask, Response, jsonify, request, stream_with_context

import candidates
import config
import llm
import matcher
import stats
import voting_places
from location import state_abbr

MAX_CONCURRENT = config.MAX_CONCURRENT
MAX_QUEUED = config.MAX_QUEUED
KEEPALIVE_SECONDS = 5

app = Flask(__name__)


@app.after_request
def allow_browsers(resp):
    """The web app is served from a different origin (e.g. :8081), so browsers need CORS.
    Flask answers the OPTIONS preflight itself; this adds the headers to it and every reply."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

def generate_response_task(data: dict, emit, cancelled: threading.Event):
    """
    data      -> the JSON the client POSTed
    emit      -> emit(event_name, payload) streams an event to the client
    cancelled -> threading.Event; set when the client disconnects.
                 Check it often (or pass it into long-running calls).
    Return value becomes the "result" event.
    """
    # Real work: the app sends {"state", "city", "answers": [...]}
    if "answers" in data:
        result = matcher.run_match(data, emit, cancelled)
        if result is not None and not cancelled.is_set():
            stats.record_decision()
        return result

    # Demo task (curl test)
    steps = int(data.get("steps", 5))
    for i in range(steps):
        if cancelled.is_set():
            return None  # stop early; nobody is listening anymore
        time.sleep(1)
        emit("progress", {"step": i + 1, "of": steps})
    return {"echo": data, "message": "done"}


_DONE = object()

class Job:
    def __init__(self, data):
        self.id = uuid.uuid4().hex[:8]
        self.data = data
        self.cancel_event = threading.Event()
        self.events = deque()
        self._cv = threading.Condition()

    def emit(self, event, payload=None):
        with self._cv:
            self.events.append((event, payload))
            self._cv.notify()

    def finish(self):
        with self._cv:
            self.events.append(_DONE)
            self._cv.notify()

    def next_event(self, timeout):
        """Block up to `timeout` seconds. Returns an event, _DONE, or None."""
        with self._cv:
            if not self.events:
                self._cv.wait(timeout)
            return self.events.popleft() if self.events else None


class QueueFull(Exception):
    pass

class Scheduler:
    def __init__(self, workers, max_queued):
        self.max_queued = max_queued
        self.pending = deque()
        self.cond = threading.Condition()
        for n in range(workers):
            threading.Thread(target=self._worker, name=f"worker-{n}", daemon=True).start()

    def submit(self, job):
        with self.cond:
            if len(self.pending) >= self.max_queued:
                raise QueueFull
            self.pending.append(job)
            self.cond.notify()

    def position(self, job):
        """1-based place in line, or 0 if not waiting (running/finished)."""
        with self.cond:
            try:
                return list(self.pending).index(job) + 1
            except ValueError:
                return 0

    def cancel(self, job):
        job.cancel_event.set()
        with self.cond:
            try:
                self.pending.remove(job)
            except ValueError:
                pass

    def _worker(self):
        while True:
            with self.cond:
                while not self.pending:
                    self.cond.wait()
                job = self.pending.popleft()
            if job.cancel_event.is_set():
                job.finish()
                continue
            job.emit("started", {"id": job.id})
            try:
                result = generate_response_task(job.data, job.emit, job.cancel_event)
                if not job.cancel_event.is_set():
                    job.emit("result", result)
            except Exception as e:  # noqa: BLE001
                job.emit("error", {"message": str(e)})
            finally:
                job.finish()


scheduler = Scheduler(MAX_CONCURRENT, MAX_QUEUED)

def sse(event, payload):
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

@app.post("/run")
def run():
    data = request.get_json(silent=True) or {}
    job = Job(data)
    try:
        scheduler.submit(job)
    except QueueFull:
        return jsonify(error="queue full, try again later"), 503

    @stream_with_context
    def stream():
        try:
            last_pos = None
            idle = 0.0
            while True:
                item = job.next_event(timeout=1.0)

                if item is _DONE:
                    return
                if item is not None:
                    idle = 0.0
                    yield sse(*item)
                    continue

                pos = scheduler.position(job)
                if pos and pos != last_pos:
                    last_pos = pos
                    idle = 0.0
                    yield sse("queued", {"position": pos})
                    continue

                idle += 1.0
                if idle >= KEEPALIVE_SECONDS:
                    idle = 0.0
                    yield ": keepalive\n\n"
        finally:
            scheduler.cancel(job)

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/voting-places")
def voting_places_route():
    """?address=&city=&state=&zip=  ->  drop-off / early vote / polling locations (JSON)."""
    a = request.args
    return jsonify(voting_places.lookup(
        (a.get("address") or "").strip(), (a.get("city") or "").strip(),
        state_abbr(a.get("state")) or "", (a.get("zip") or "").strip(),
    ))

@app.post("/visit")
def visit():
    """The app calls this once per launch. Render's proxy puts the caller's IP first in
    X-Forwarded-For; locally there is no proxy, so use the socket's address."""
    ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or request.remote_addr
    device = str((request.get_json(silent=True) or {}).get("device") or "")[:64]
    return jsonify(stats.record_open(ip, device))

@app.get("/stats")
def stats_route():
    return jsonify(stats.counts())

@app.get("/status")
def status():
    with scheduler.cond:
        waiting = len(scheduler.pending)
    return jsonify(max_concurrent=MAX_CONCURRENT, waiting=waiting, app_env=config.APP_ENV,
                   provider=config.LLM_PROVIDER, model=llm.describe(),
                   candidates=len(candidates.load_candidates()))

def _warmup():
    """Load candidate files and the local model now, so the first request isn't slow."""
    try:
        print(f"{len(candidates.load_candidates())} candidates loaded.", flush=True)
        llm.warmup()
        print(f"Decision model ready: {llm.describe()}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"Could not load the decision model ({llm.describe()}): {e}", flush=True)

# Runs under both `python main.py` and gunicorn
threading.Thread(target=_warmup, daemon=True).start()

def run_server(host=config.HOST, port=config.PORT):
    app.run(host=host, port=port, threaded=True)