"""
omni_server.py — Servidor HTTP local para o Projeto Omni
Serve o frontend React + roteia chamadas de API para o BrainOrchestrator Python.
Integração LLM real via OpenAI-compatible API (Replit AI Integration ou chave própria).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
PYTHON_BACKEND = str(REPO_ROOT / "backend" / "python")

PORT = int(os.environ.get("PORT", 3001))
BASE_PATH = os.environ.get("BASE_PATH", "/").rstrip("/")  # e.g. "/omni"

OMNI_SYSTEM_PROMPT = (
    "Você é Omni, um assistente de IA cognitivo avançado criado para raciocínio "
    "profundo, planejamento e execução de tarefas complexas. Responda sempre em "
    "português do Brasil de forma clara, precisa e útil. Quando analisar código, "
    "arquiteturas ou problemas técnicos, seja detalhado e estruturado."
)


def strip_base(path: str) -> str:
    """Remove BASE_PATH prefix so /omni/api/v1/chat → /api/v1/chat."""
    if BASE_PATH and path.startswith(BASE_PATH):
        stripped = path[len(BASE_PATH):]
        return stripped if stripped.startswith("/") else "/" + stripped
    return path


def _resolve_llm_credentials() -> tuple[str, str] | None:
    """
    Resolve credenciais LLM: checa OPENAI_API_KEY primeiro,
    depois AI_INTEGRATIONS_OPENAI_API_KEY (Replit AI Integration).
    Retorna (api_key, base_url) ou None se nenhuma chave disponível.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "").strip()

    if not api_key:
        return None
    upper = api_key.upper()
    if "YOUR_" in api_key or "<<PASTE" in upper or len(api_key) < 8:
        return None

    base_url = (
        os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    )
    return api_key, base_url.rstrip("/")


def call_llm_api(message: str, history: list | None = None) -> dict | None:
    """
    Chamada real à API LLM compatível com OpenAI (chat/completions).
    Retorna dict com 'response' em caso de sucesso, None se falhar ou não configurado.
    """
    creds = _resolve_llm_credentials()
    if not creds:
        return None
    api_key, base_url = creds

    messages: list[dict] = [{"role": "system", "content": OMNI_SYSTEM_PROMPT}]
    for h in (history or []):
        role = str(h.get("role", "user")).strip()
        content = str(h.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    payload_bytes = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choice = data["choices"][0]
        content = choice["message"]["content"]
        return {
            "response": content,
            "provider": "openai",
            "model": data.get("model", model),
            "stop_reason": choice.get("finish_reason", "stop"),
            "runtime_mode": "LLM_ACTIVE",
        }
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError, OSError):
        return None


def call_python_orchestrator(message: str, history: list | None = None) -> dict:
    """Chama backend/python/main.py como subprocess e retorna JSON."""
    payload = json.dumps({
        "message": message,
        "history": history or [],
        "capabilities": [],
        "memory": {},
        "session": {"session_id": str(uuid.uuid4())},
    })

    # Propaga credenciais LLM ao subprocess (alias das chaves Replit AI Integration)
    extra_env: dict[str, str] = {}
    creds = _resolve_llm_credentials()
    if creds:
        api_key, base_url = creds
        if not os.environ.get("OPENAI_API_KEY"):
            extra_env["OPENAI_API_KEY"] = api_key
        if not os.environ.get("OPENAI_BASE_URL"):
            extra_env["OPENAI_BASE_URL"] = base_url

    try:
        result = subprocess.run(
            [sys.executable, "main.py", payload],
            capture_output=True,
            text=True,
            cwd=PYTHON_BACKEND,
            timeout=60,
            env={**os.environ, "PYTHONPATH": PYTHON_BACKEND, **extra_env},
        )
        raw = result.stdout.strip()
        if not raw:
            return {"response": "[sem resposta do orquestrador]", "stop_reason": "empty"}
        return json.loads(raw)
    except subprocess.TimeoutExpired:
        return {"response": "[timeout: orquestrador demorou mais de 60s]", "stop_reason": "timeout"}
    except json.JSONDecodeError as e:
        return {"response": f"[erro ao parsear resposta: {e}]", "stop_reason": "parse_error"}
    except Exception as e:  # noqa: BLE001
        return {"response": f"[erro interno: {e}]", "stop_reason": "server_error"}


def make_status_response() -> dict:
    creds = _resolve_llm_credentials()
    has_llm = creds is not None
    provider = "openai" if has_llm else "local-heuristic"
    runtime_mode = "LLM_ACTIVE" if has_llm else "LOCAL_HEURISTIC"
    return {
        "status": "ok",
        "runtime_mode": runtime_mode,
        "provider": provider,
        "version": "v2.1-remediation",
        "llm_active": has_llm,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def serve_static(handler: "OmniHandler", path: str) -> bool:
    """Tenta servir arquivo estático do frontend/dist. Retorna True se servido."""
    if not FRONTEND_DIST.exists():
        return False

    clean = path.lstrip("/") or "index.html"
    file_path = FRONTEND_DIST / clean

    # SPA fallback — qualquer rota não-encontrada serve index.html
    if not file_path.exists() or file_path.is_dir():
        file_path = FRONTEND_DIST / "index.html"

    if not file_path.exists():
        return False

    ext = file_path.suffix.lower()
    mime = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".ico": "image/x-icon",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".map": "application/json",
    }.get(ext, "application/octet-stream")

    data = file_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(data)
    return True


class OmniHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D102
        pass  # silencia logs verbosos do http.server

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        raw_path = urlparse(self.path).path
        path = strip_base(raw_path)

        # Health / status
        if path in ("/api/v1/status", "/api/v1/health", "/health", "/api/healthz"):
            self._send_json(200, make_status_response())
            return

        # Runtime signals summary
        if path in ("/api/v1/runtime/signals/summary", "/api/v1/runtime/signals"):
            self._send_json(200, {
                "signals": [],
                "summary": "Rodando em modo local — sem sinais de runtime externos.",
            })
            return

        # Milestones / PRs
        if path.startswith("/api/v1/milestones") or path.startswith("/api/v1/pr"):
            self._send_json(200, {"items": [], "total": 0})
            return

        # Strategy, observability
        if path.startswith("/api/v1/strategy") or path.startswith("/api/v1/observability"):
            self._send_json(200, {"status": "ok", "data": {}})
            return

        # Demais rotas /api/*
        if path.startswith("/api/"):
            self._send_json(200, {"status": "ok"})
            return

        # Arquivos estáticos do frontend (usa path original sem strip)
        # O frontend é construído com base=/omni/ então os assets chegam como /omni/assets/...
        if not serve_static(self, path):
            # fallback SPA — serve index.html
            serve_static(self, "index.html")

    def do_POST(self) -> None:  # noqa: N802
        raw_path = urlparse(self.path).path
        path = strip_base(raw_path)
        body = self._read_body()

        if path in ("/api/v1/chat", "/chat"):
            message = body.get("message", "").strip()
            history = body.get("history", [])

            if not message:
                self._send_json(400, {"error": "message obrigatória"})
                return

            # Tenta LLM real primeiro; cai no orquestrador Python se não disponível/falhar
            result = call_llm_api(message, history)
            if result is None:
                result = call_python_orchestrator(message, history)

            self._send_json(200, result)
            return

        self._send_json(404, {"error": f"rota POST não encontrada: {path}"})


def main() -> None:
    creds = _resolve_llm_credentials()
    llm_status = "✅ LLM ativo (OpenAI-compatible)" if creds else "⚠️  Modo local-heuristic (sem chave LLM)"
    print(f"[omni] Servidor iniciado em http://localhost:{PORT}", flush=True)
    print(f"[omni] BASE_PATH: '{BASE_PATH}' (prefixo removido das rotas)", flush=True)
    print(f"[omni] Frontend: {'✅ ' + str(FRONTEND_DIST) if FRONTEND_DIST.exists() else '⚠️  frontend/dist não encontrado'}", flush=True)
    print(f"[omni] Backend Python: {PYTHON_BACKEND}", flush=True)
    print(f"[omni] LLM: {llm_status}", flush=True)
    print("[omni] Ctrl+C para parar\n", flush=True)

    server = HTTPServer(("0.0.0.0", PORT), OmniHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[omni] Servidor encerrado.")


if __name__ == "__main__":
    main()
