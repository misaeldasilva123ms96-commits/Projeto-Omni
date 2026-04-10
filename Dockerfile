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
    BASE_DIR=/app \
    PYTHON_BASE_DIR=/app/backend/python \
    PYTHON_ENTRY=/app/backend/python/main.py \
    PYTHON_BIN=python3 \
    NODE_BIN=node \
    PORT=3001

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY backend/python ./backend/python
COPY backend/rust ./backend/rust
COPY js-runner ./js-runner
COPY src ./src
COPY contract ./contract
COPY --from=rust-builder /build/backend/rust/target/release/omini-api /usr/local/bin/omini-api

RUN pip3 install --no-cache-dir -r backend/python/requirements.txt

EXPOSE 3001

CMD ["omini-api"]
