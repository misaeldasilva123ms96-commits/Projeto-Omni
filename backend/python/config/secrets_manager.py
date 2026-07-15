"""Centralized provider secrets — single read path; no logging of values."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .provider_credential_adapter import inject_credential_store_credentials

__all__ = [
    "SecretError",
    "build_controlled_os_environ_base",
    "describe_configuration",
    "describe_configuration_safe",
    "get_secret",
    "merge_provider_credentials",
]


class SecretError(Exception):
    """Raised when a logical secret is unknown, missing, or still a placeholder."""


def _mapping() -> dict[str, str]:
    return {
        "groq": "GROQ_API_KEY",
        "groq_model": "GROQ_MODEL",
        "openrouter": "OPENROUTER_API_KEY",
        "openrouter_model": "OPENROUTER_MODEL",
        "openai": "OPENAI_API_KEY",
        "openai_model": "OPENAI_MODEL",
        "anthropic": "ANTHROPIC_API_KEY",
        "anthropic_model": "ANTHROPIC_MODEL",
        "gemini": "GEMINI_API_KEY",
        "gemini_model": "GEMINI_MODEL",
        "deepseek": "DEEPSEEK_API_KEY",
        "deepseek_model": "DEEPSEEK_MODEL",
        "ollama": "OLLAMA_URL",
        "ollama_model": "OLLAMA_MODEL",
        "ollama_api_key": "OLLAMA_API_KEY",
        "lmstudio": "LMSTUDIO_URL",
        "lmstudio_model": "LMSTUDIO_MODEL",
        "lmstudio_api_key": "LMSTUDIO_API_KEY",
        "codex": "CODEX_API_KEY",
        "supabase_url": "SUPABASE_URL",
        "supabase_anon": "SUPABASE_ANON_KEY",
    }


def get_secret(name: str) -> str:
    """Return a validated secret value for the logical provider name."""
    logical = str(name or "").strip().lower()
    env_name = _mapping().get(logical)
    if not env_name:
        raise SecretError(f"Unknown secret: {logical}")

    raw = os.environ.get(env_name)
    value = str(raw).strip() if raw is not None else ""
    if not value:
        raise SecretError(f"Missing or invalid secret: {env_name}")

    upper = value.upper()
    if "YOUR_" in value or "<<PASTE" in upper:
        raise SecretError(f"Missing or invalid secret: {env_name}")

    return value


def describe_configuration() -> dict[str, str]:
    """Safe status map for debug/health — never returns secret values."""
    mapping = {
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "ollama": "OLLAMA_URL",
        "lmstudio": "LMSTUDIO_URL",
        "codex": "CODEX_API_KEY",
        "supabase": "SUPABASE_ANON_KEY",
    }
    result: dict[str, str] = {}
    for key, env_name in mapping.items():
        raw = os.environ.get(env_name)
        value = str(raw).strip() if raw is not None else ""
        upper = value.upper()
        if value and "YOUR_" not in value and "<<PASTE" not in upper:
            result[key] = "configured"
        else:
            result[key] = "missing"
    return result


def describe_configuration_safe() -> dict[str, Any]:
    """Backward-compatible alias for callers expecting a nested payload."""
    return {"providers": describe_configuration()}


def build_controlled_os_environ_base() -> dict[str, str]:
    """
    Minimal inherited process environment for Node subprocesses.

    Does not copy the full parent environ (reduces accidental leak surface).
    Includes essential Windows variables for Node.js crypto initialization.
    """
    env: dict[str, str] = {}
    path_val = os.environ.get("PATH") or os.environ.get("Path")
    if path_val:
        env["PATH"] = str(path_val)
    # Essential Windows variables for Node.js subprocesses (incl. crypto)
    essential_keys = (
        "PATHEXT",
        "COMSPEC",
        "SystemRoot",
        "SYSTEMROOT",
        "WINDIR",
        "TMP",
        "TEMP",
        "USERPROFILE",
        "HOME",
        "LANG",
        "LC_ALL",
        "PYTHONPATH",
        "NODE_PATH",
        "NODE_OPTIONS",
        # Additional Windows essentials for Node.js crypto
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SYSTEMDRIVE",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "PUBLIC",
        "ALLUSERSPROFILE",
        "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)",
        "COMMONPROGRAMW6432",
        "COMPUTERNAME",
        "USERDOMAIN",
        "USERDOMAIN_ROAMING_PROFILE",
        "USERNAME",
        "LOGONSERVER",
        "SESSIONNAME",
    )
    for key in essential_keys:
        val = os.environ.get(key)
        if val is not None and str(val).strip():
            env[key] = str(val)
    if os.name == "nt":
        windows_root = (
            env.get("SystemRoot")
            or env.get("SYSTEMROOT")
            or env.get("WINDIR")
            or (r"C:\Windows" if Path(r"C:\Windows").exists() else "")
        )
        if windows_root:
            env.setdefault("SystemRoot", windows_root)
            env.setdefault("SYSTEMROOT", windows_root)
            env.setdefault("WINDIR", windows_root)
            cmd_path = Path(windows_root) / "System32" / "cmd.exe"
            if cmd_path.exists():
                env.setdefault("COMSPEC", str(cmd_path))
    return env


def merge_provider_credentials(
    env: dict[str, str], user_id: str | None = None
) -> dict[str, str]:
    """Merge validated provider keys into env; skips missing/invalid without raising.

    BYOK precedence:
    - CredentialStore entries override the same env keys when ``user_id`` is
      provided and the store is available.
    - Otherwise, existing environment variables are used unchanged.
    """
    merged = inject_credential_store_credentials(user_id=user_id, env=env)
    for logical in (
        "groq",
        "groq_model",
        "openrouter",
        "openrouter_model",
        "openai",
        "openai_model",
        "anthropic",
        "anthropic_model",
        "gemini",
        "gemini_model",
        "deepseek",
        "deepseek_model",
        "ollama",
        "ollama_model",
        "ollama_api_key",
        "lmstudio",
        "lmstudio_model",
        "lmstudio_api_key",
        "codex",
        "supabase_url",
        "supabase_anon",
    ):
        try:
            val = get_secret(logical)
        except SecretError:
            continue
        env_name = _mapping()[logical]
        merged[env_name] = val
    cid = os.environ.get("CHATGPT_ACCOUNT_ID")
    if cid is not None:
        s = str(cid).strip()
        upper = s.upper()
        if s and "YOUR_" not in s and "<<PASTE" not in upper:
            merged["CHATGPT_ACCOUNT_ID"] = s
    return merged
