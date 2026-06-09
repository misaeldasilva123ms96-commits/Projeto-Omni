"""DEV-ONLY diagnostic; do not paste verbose output publicly without redaction."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_RUNTIME_DIR = Path(__file__).resolve().parent.parent  # brain/runtime
_PYTHON_DIR = _RUNTIME_DIR.parent.parent  # backend/python
_PROJECT_ROOT = _PYTHON_DIR.parent.parent  # project root

sys.path.insert(0, str(_PYTHON_DIR))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "python"))

HEADER = "=" * 72
SUBHEADER = "-" * 72
SECRET_KEY_PATTERN = re.compile(
    r"(token|secret|password|passwd|pwd|api[_-]?key|access[_-]?key|private[_-]?key|credential|auth|bearer)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{12,}|"
    r"(sk-[A-Za-z0-9_-]{12,})|"
    r"(gh[pousr]_[A-Za-z0-9_]{12,})|"
    r"(xox[baprs]-[A-Za-z0-9-]{12,})"
)


def _colorize(label: str, status: str) -> str:
    if status in ("ok", "success", "live", "true", "passed"):
        return f"\033[92m{label}\033[0m"
    if status in ("fallback", "fail", "degraded", "false", "error"):
        return f"\033[91m{label}\033[0m"
    if status in ("bridge_execution_request", "local_direct_response", "matcher_shortcut"):
        return f"\033[94m{label}\033[0m"
    if status in ("true_action_execution",):
        return f"\033[93m{label}\033[0m"
    return label


def _redact(value: Any, *, key: str = "") -> str:
    text = str(value or "")
    if not text:
        return text
    if SECRET_KEY_PATTERN.search(str(key or "")):
        return "<redacted>"
    return SECRET_VALUE_PATTERN.sub(lambda match: (match.group(1) or "") + "<redacted>", text)


def _import_or_fail(module_path: str, name: str):
    try:
        mod = __import__(module_path, fromlist=[name])
        return getattr(mod, name)
    except ImportError as e:
        print(f"  \033[91mERROR: Nao foi possivel importar '{name}' de '{module_path}': {e}\033[0m")
        return None


def _detect_env() -> dict[str, Any]:
    env = {
        "BASE_DIR": os.getenv("BASE_DIR", ""),
        "OMINI_JS_RUNTIME_BIN": os.getenv("OMINI_JS_RUNTIME_BIN", ""),
        "NODE_BIN": os.getenv("NODE_BIN", ""),
        "OMINI_RUNTIME_MODE": os.getenv("OMINI_RUNTIME_MODE", ""),
        "OMINI_ALLOW_SHELL_TOOLS": os.getenv("OMINI_ALLOW_SHELL_TOOLS", ""),
        "OMINI_LOG_LEVEL": os.getenv("OMINI_LOG_LEVEL", ""),
        "PATH (primeiros 200 chars)": os.getenv("PATH", "")[:200],
    }
    node_path = os.getenv("PATH", "")
    node_found = None
    for p in node_path.split(";"):
        candidate = Path(p) / "node.exe"
        if candidate.exists():
            node_found = str(candidate)
            break
        candidate = Path(p) / "node"
        if candidate.exists():
            node_found = str(candidate)
            break
    env["_node_on_path"] = node_found or "not found"
    return env


def _print_env(env: dict[str, Any]) -> None:
    print(f"\n  {SUBHEADER}")
    print("  ENVIRONMENT VARIABLES (relevantes)")
    print(f"  {SUBHEADER}")
    for k, v in env.items():
        if k.startswith("_"):
            continue
        if v:
            print(f"    {k} = {_redact(v, key=k)}")
        else:
            print(f"    {k} = \033[90m<not set>\033[0m")
    print(f"    Node on PATH: {_redact(env.get('_node_on_path', 'unknown'), key='_node_on_path')}")


def print_debug_report(
    *,
    prompt: str,
    memory_store: dict[str, Any] | None = None,
    available_capabilities: list[dict[str, str]] | None = None,
    verbose: bool = False,
    timeout_seconds: int = 15,
) -> None:
    resolve_node_command_context = _import_or_fail(
        "brain.runtime.node_runner", "resolve_node_command_context"
    )
    call_node_with_preflight = _import_or_fail(
        "brain.runtime.node_transport", "call_node_with_preflight"
    )
    run_node_subprocess = _import_or_fail(
        "brain.runtime.node_transport", "run_node_subprocess"
    )
    interpret_node_payload = _import_or_fail(
        "brain.runtime.observability.runtime_lane_classifier",
        "interpret_node_payload",
    )
    normalize_node_outcome = _import_or_fail(
        "brain.runtime.observability.runtime_lane_classifier",
        "normalize_node_outcome",
    )
    BrainPaths = _import_or_fail("brain.runtime.orchestrator", "BrainPaths")
    JSRuntimeAdapter = _import_or_fail(
        "brain.runtime.js_runtime_adapter", "JSRuntimeAdapter"
    )

    if any(fn is None for fn in [
        resolve_node_command_context,
        call_node_with_preflight,
        run_node_subprocess,
        interpret_node_payload,
        normalize_node_outcome,
        BrainPaths,
        JSRuntimeAdapter,
    ]):
        print("\n  \033[91mProjeto nao configurado corretamente. Verifique o PYTHONPATH.\033[0m")
        return

    print(f"\n{HEADER}")
    print("  DEBUG NODE PRIMARY PATH")
    print(f"{HEADER}")

    print(f"\n  Prompt: \"{prompt}\"")
    print(f"  Timeout: {timeout_seconds}s")
    print(f"  Verbose: {verbose}")
    print(f"  Python: {sys.executable}")

    paths = BrainPaths.from_entrypoint(Path(__file__))
    print(f"\n  Project root: {paths.root}")
    print(f"  Python root: {paths.python_root}")
    print(f"  JS runner: {paths.js_runner}")
    print(f"  Runner exists: {paths.js_runner.exists()}")

    _print_env(_detect_env())

    adapter = JSRuntimeAdapter(paths.root)
    runtime_sel = adapter.select_runtime()
    print(f"\n  {SUBHEADER}")
    print("  JS RUNTIME SELECTION")
    print(f"  {SUBHEADER}")
    print(f"    runtime: {runtime_sel.runtime_name}")
    print(f"    executable: {runtime_sel.executable}")
    print(f"    source: {runtime_sel.source}")
    print(f"    node_available: {runtime_sel.node_available}")
    print(f"    bun_available: {runtime_sel.bun_available}")

    history = (memory_store or {}).get("history", [])
    memory = (memory_store or {}).get("user", {})
    compact_history = _import_or_fail("brain.runtime.node_runner", "compact_history_for_node")
    if compact_history:
        hist = compact_history(history)
    else:
        hist = history[-6:] if history else []

    payload = json.dumps(
        {
            "message": prompt,
            "memory": memory,
            "history": hist,
            "summary": "",
            "capabilities": available_capabilities or [],
            "session": {"session_id": "debug-node-primary-path"},
        },
        ensure_ascii=False,
    )

    diagnostics = resolve_node_command_context(
        paths=paths,
        js_runtime_adapter=adapter,
        payload=payload,
    )

    print(f"\n  {SUBHEADER}")
    print("  PREFLIGHT")
    print(f"  {SUBHEADER}")
    preflight_keys = [
        ("node_resolved", diagnostics.get("node_resolved"), "ok", "fail"),
        ("runner_exists", diagnostics.get("runner_exists"), "ok", "fail"),
        ("cwd_exists", diagnostics.get("cwd_exists"), "ok", "fail"),
        ("adapter_exists", diagnostics.get("adapter_exists"), "ok", "fail"),
        ("compiled_runner_artifact_exists", diagnostics.get("compiled_runner_artifact_exists"), "ok", "fail"),
        ("missing_paths", diagnostics.get("missing_paths"), "ok", "fail"),
    ]
    all_preflight_ok = True
    for key, val, pass_val, fail_val in preflight_keys:
        status = pass_val if val else fail_val
        if not val:
            all_preflight_ok = False
        print(f"    {key}: {_colorize(str(val), status)}")
    if not all_preflight_ok:
        missing = diagnostics.get("missing_paths", [])
        if missing:
            print(f"\n    \033[91mMissing paths:\033[0m")
            for p in missing:
                print(f"      - {p}")

    print(f"\n  {SUBHEADER}")
    print("  SUBPROCESS EXECUTION")
    print(f"  {SUBHEADER}")
    print(f"    Command: {_redact(' '.join(str(x) for x in diagnostics.get('command', [])), key='command')}")
    print(f"    CWD: {_redact(diagnostics.get('cwd', ''), key='cwd')}")
    print(f"    Payload size: {len(payload)} chars")

    transport = run_node_subprocess(
        diagnostics=diagnostics,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )

    transport_ok = bool(transport.get("ok", False))
    transport_stage = str(transport.get("stage", "unknown"))
    transport_reason = str(transport.get("reason_code", "unknown"))
    print(f"    transport.ok: {_colorize(str(transport_ok), 'ok' if transport_ok else 'fallback')}")
    print(f"    transport.stage: {transport_stage}")
    print(f"    transport.reason_code: {transport_reason}")
    print(f"    returncode: {transport.get('returncode', 'N/A')}")

    stdout = str(transport.get("stdout", "") or "")
    stderr = str(transport.get("stderr", "") or "")
    if verbose:
        print(f"\n    STDOUT ({len(stdout)} chars):")
        print(f"      {_redact(stdout[:2000], key='stdout')}")
        if stderr:
            print(f"\n    STDERR ({len(stderr)} chars):")
            print(f"      {_redact(stderr[:2000], key='stderr')}")
    else:
        print(f"    stdout: {len(stdout)} chars (use --verbose para ver o conteudo)")
        if stderr:
            print(f"    stderr: {len(stderr)} chars")
            print(f"    \033[93mstderr preview: {_redact(stderr[:300], key='stderr')}\033[0m")

    parsed = transport.get("parsed")
    print(f"\n  {SUBHEADER}")
    print("  PARSED JSON")
    print(f"  {SUBHEADER}")
    if isinstance(parsed, dict):
        keys = list(parsed.keys())
        print(f"    Keys: {keys}")
        for k in keys:
            v = parsed[k]
            if isinstance(v, str):
                print(f"    {k}: \"{_redact(v[:200], key=str(k))}\"")
            elif isinstance(v, dict):
                print(f"    {k}: <dict, {len(v)} keys>")
            elif isinstance(v, list):
                print(f"    {k}: <list, {len(v)} items>")
            else:
                print(f"    {k}: {_redact(v, key=str(k))}")
        response_text = str(parsed.get("response", "") or "")
        print(f"\n    response: \"{_redact(response_text[:300], key='response')}\"" + ("..." if len(response_text) > 300 else ""))
        exec_req = parsed.get("execution_request")
        if isinstance(exec_req, dict):
            actions = exec_req.get("actions", [])
            print(f"    execution_request.actions: {len(actions) if isinstance(actions, list) else 'N/A'}")
        hint = parsed.get("cognitive_runtime_hint")
        if isinstance(hint, dict):
            print(f"    cognitive_runtime_hint.lane: {hint.get('lane', 'N/A')}")
            print(f"    cognitive_runtime_hint.detail: {_redact(str(hint.get('detail', ''))[:200], key='cognitive_runtime_hint.detail')}")
    else:
        print(f"    \033[91mNot a dict: {type(parsed).__name__}\033[0m")

    print(f"\n  {SUBHEADER}")
    print("  SEMANTIC CLASSIFICATION")
    print(f"  {SUBHEADER}")
    semantic = interpret_node_payload(parsed=parsed, stdout=stdout)
    semantic_lane = str(semantic.get("semantic_lane", "") or "")
    is_fallback = bool(semantic.get("fallback", True))
    reason_code = str(semantic.get("reason_code", "") or "")
    response_text_sem = str(semantic.get("response_text", "") or "")
    print(f"    semantic_lane: {_colorize(semantic_lane, semantic_lane)}")
    print(f"    fallback: {_colorize(str(is_fallback), 'fallback' if is_fallback else 'success')}")
    print(f"    reason_code: {_redact(reason_code, key='reason_code')}")
    print(f"    response_text ({len(response_text_sem)} chars): \"{_redact(response_text_sem[:300], key='response_text')}\"")

    outcome = semantic.get("node_outcome")
    if isinstance(outcome, dict):
        print(f"\n  {SUBHEADER}")
        print("  NODE OUTCOME (normalizado)")
        print(f"  {SUBHEADER}")
        outcome_keys = [
            "transport_status", "semantic_lane", "reason_code",
            "node_hint_lane", "provider_actual", "failure_class",
            "has_execution_request", "has_actions", "response_present",
        ]
        for k in outcome_keys:
            v = outcome.get(k, "N/A")
            print(f"    {k}: {v}")
        rt = outcome.get("runtime_truth")
        if isinstance(rt, dict):
            print(f"    runtime_truth.intent: {rt.get('intent', 'N/A')}")
            print(f"    runtime_truth.intent_source: {rt.get('intent_source', 'N/A')}")

    print(f"\n  {SUBHEADER}")
    print("  VEREDITO")
    print(f"  {SUBHEADER}")
    if transport_ok and isinstance(parsed, dict) and not is_fallback:
        print(f"  {_colorize('PRIMARY PATH ATIVO', 'ok')} — Node retornou resposta valida, classificacao semantica bem-sucedida.")
        print(f"  Lane: {semantic_lane}, Motivo: {reason_code}")
    elif transport_ok and isinstance(parsed, dict) and is_fallback:
        print(f"  {_colorize('PRIMARY PATH FALHOU (CLASSIFICACAO)', 'fallback')} — Transporte OK, mas interpretacao semantica resultou em fallback.")
        print(f"  Motivo: {reason_code}, Lane: {semantic_lane}")
        print(f"  \033[93m  Diagnostico: Node retornou JSON valido, mas o classificador decidiu por fallback.\033[0m")
        print(f"  \033[93m  Verifique cognitive_runtime_hint, execution_request e response text.\033[0m")
    elif not transport_ok:
        print(f"  {_colorize('PRIMARY PATH FALHOU (TRANSPORTE)', 'fallback')} — Subprocesso Node falhou.")
        print(f"  Stage: {_redact(transport_stage, key='transport_stage')}, Motivo: {_redact(transport_reason, key='transport_reason')}")
        print(f"  \033[93m  Diagnostico: O Node nao produziu saida valida. Verifique ambiente, logs e stderr.\033[0m")
        if stderr:
            print(f"  \033[93m  stderr: {_redact(stderr[:500], key='stderr')}\033[0m")
    else:
        print(f"  {_colorize('PRIMARY PATH FALHOU (DESCONHECIDO)', 'fallback')} — Nao foi possivel determinar a causa.")

    print(f"\n{HEADER}")
    print(f"  FIM DO DEBUG")
    print(f"{HEADER}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug da chamada primaria ao Node runtime (Bloco 3)"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="responda apenas OK",
        help="Prompt a ser enviado para o Node (default: 'responda apenas OK')",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe stdout/stderr completos do subprocesso Node",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout em segundos para o subprocesso Node (default: 15)",
    )
    args = parser.parse_args()

    print_debug_report(
        prompt=args.prompt,
        verbose=args.verbose,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    main()
