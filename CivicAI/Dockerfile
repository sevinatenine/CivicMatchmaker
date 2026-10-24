# API server image for hosted mode (Render, see render.yaml). Decisions go through OpenRouter,
# so there is no torch / Julia-1 here: the image is small and starts fast.
#   docker build -t civicmatchmaker-api CivicAI
#   docker run --rm -p 4000:4000 --env-file .env -e APP_ENV=hosted civicmatchmaker-api
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=hosted \
    LLM_PROVIDER=openrouter \
    PORT=4000

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 4000
# One process: jobs and caches live in memory. Threads serve the SSE streams.
CMD ["sh", "-c", "exec gunicorn -w 1 -k gthread --threads 32 --timeout 0 -b 0.0.0.0:${PORT} server:app"]
