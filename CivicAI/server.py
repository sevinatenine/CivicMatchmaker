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

Run:   python main.py
Test:  curl -N -X POST localhost:4000/run -H 'Content-Type: application/json' -d '{"steps": 8}'
       (Ctrl-C in curl to simulate a disconnect)

NOTE: state lives in memory, so run a SINGLE process. For production use e.g.
       gunicorn -w 1 -k gthread --threads 100 server:app
"""

import json
import os
import threading
import time
import uuid
from collections import deque

from flask import Flask, Response, jsonify, request, stream_with_context

import ai

MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", 2))
MAX_QUEUED = int(os.environ.get("MAX_QUEUED", 50))
KEEPALIVE_SECONDS = 5

app = Flask(__name__)

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
        return ai.run_match(data, emit, cancelled)

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

@app.get("/status")
def status():
    with scheduler.cond:
        waiting = len(scheduler.pending)
    return jsonify(max_concurrent=MAX_CONCURRENT, waiting=waiting)

def _warmup():
    try:
        ai.warmup()
        print("Julia 1 loaded.")
    except Exception as e:  # noqa: BLE001
        print(f"Could not load Julia 1: {e}")

def run_server(port=4001, host="0.0.0.0"):
    # Load the model now so the first request isn't slow
    threading.Thread(target=_warmup, daemon=True).start()
    app.run(host=host, port=port, threaded=True)