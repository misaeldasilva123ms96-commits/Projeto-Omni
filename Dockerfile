FROM rust:1.87-bookworm AS rust-builder

WORKDIR /build

COPY backend/rust/Cargo.toml backend/rust/Cargo.lock ./backend/rust/
COPY backend/rust/crates ./backend/rust/crates
COPY backend/rust/src ./backend/rust/src

WORKDIR /build/backend/rust
RUN cargo build --release

FROM node:20-bookworm-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    BASE_DIR=/app \
    PYTHON_BASE_DIR=/app/backend/python \
    PYTHON_ENTRY=/app/backend/python/main.py \
    PYTHON_BIN=/opt/venv/bin/python \
    NODE_BIN=node \
    PORT=3001

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY backend/python/requirements.txt ./backend/python/requirements.txt
RUN if [ -f backend/python/requirements.txt ] \
      && grep -Eq '^[[:space:]]*[^#[:space:]][^#]*$' backend/python/requirements.txt; then \
        /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
        && /opt/venv/bin/pip install --no-cache-dir -r backend/python/requirements.txt; \
    else \
        echo "Skipping pip install: backend/python/requirements.txt has no active dependencies."; \
    fi

COPY backend/python ./backend/python
COPY backend/rust ./backend/rust
COPY core ./core
COPY configs ./configs
COPY features ./features
COPY js-runner ./js-runner
COPY observability ./observability
COPY platform ./platform
COPY runtime ./runtime
COPY storage ./storage
COPY src ./src
COPY contract ./contract
COPY --from=rust-builder /build/backend/rust/target/release/omini-api /usr/local/bin/omini-api

EXPOSE 3001

CMD ["omini-api"]
