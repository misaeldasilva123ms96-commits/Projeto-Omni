FROM python:3.11-slim

WORKDIR /app

# Python brain runtime
COPY backend/python/brain ./backend/python/brain
COPY backend/python/main.py ./backend/python/main.py
COPY backend/python/brain_registry.py ./backend/python/brain_registry.py
COPY backend/python/transcript_store.py ./backend/python/transcript_store.py
COPY backend/python/requirements.txt ./backend/python/requirements.txt
COPY backend/python/memory.json ./backend/python/memory.json
COPY backend/python/memory ./backend/python/memory
COPY backend/python/transcripts ./backend/python/transcripts
COPY backend/python/brain/runtime/sessions ./backend/python/brain/runtime/sessions
COPY js-runner ./js-runner
COPY src ./src
COPY contract ./contract

RUN pip install --no-cache-dir -r backend/python/requirements.txt

WORKDIR /app/backend/python

CMD ["python", "main.py"]
