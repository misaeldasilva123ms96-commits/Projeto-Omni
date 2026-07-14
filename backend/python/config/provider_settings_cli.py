#!/usr/bin/env python3
"""CLI bridge for ProviderSettingsController — called from Rust boundary.

Security: secrets are received via stdin (NOT argv) to prevent exposure
through /proc/<pid>/cmdline on Unix systems.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure backend/python is in path
BACKEND_PYTHON = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_PYTHON))

from config.provider_settings_controller import (  # noqa: E402
    ProviderSettingsController,
    list_providers,
    save_provider,
    update_provider,
    delete_provider,
    test_provider,
)


def _read_secret_from_stdin() -> str:
    """Read exactly one line from stdin as the secret value.

    The Rust side writes the secret followed by a newline, then closes
    the pipe.  This function strips the trailing newline.
    """
    return sys.stdin.readline().strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: provider_settings_cli <command> [args...]"}))
        return 1

    command = sys.argv[1]

    try:
        if command == "list":
            if len(sys.argv) != 3:
                print(json.dumps({"error": "usage: provider_settings_cli list <user_id>"}))
                return 1
            user_id = sys.argv[2]
            result = list_providers(user_id=user_id)
            print(json.dumps(result))
            return 0

        elif command == "save":
            if len(sys.argv) != 4:
                print(
                    json.dumps(
                        {
                            "error": "usage: provider_settings_cli save <user_id> <provider_id>  (secret via stdin)"
                        }
                    )
                )
                return 1
            user_id = sys.argv[2]
            provider_id = sys.argv[3]
            secret = _read_secret_from_stdin()
            result = save_provider(user_id=user_id, provider_id=provider_id, secret=secret)
            print(json.dumps(result))
            return 0

        elif command == "update":
            if len(sys.argv) != 4:
                print(
                    json.dumps(
                        {
                            "error": "usage: provider_settings_cli update <user_id> <provider_id>  (secret via stdin)"
                        }
                    )
                )
                return 1
            user_id = sys.argv[2]
            provider_id = sys.argv[3]
            secret = _read_secret_from_stdin()
            result = update_provider(user_id=user_id, provider_id=provider_id, secret=secret)
            print(json.dumps(result))
            return 0

        elif command == "delete":
            if len(sys.argv) != 4:
                print(
                    json.dumps(
                        {"error": "usage: provider_settings_cli delete <user_id> <provider_id>"}
                    )
                )
                return 1
            user_id, provider_id = sys.argv[2], sys.argv[3]
            result = delete_provider(user_id=user_id, provider_id=provider_id)
            print(json.dumps(result))
            return 0

        elif command == "test":
            if len(sys.argv) != 4:
                print(
                    json.dumps(
                        {
                            "error": "usage: provider_settings_cli test <user_id> <provider_id>  (secret via stdin)"
                        }
                    )
                )
                return 1
            user_id, provider_id = sys.argv[2], sys.argv[3]
            secret = _read_secret_from_stdin()
            result = test_provider(
                user_id=user_id,
                provider_id=provider_id,
                secret=secret,
            )
            print(json.dumps(result))
            return 0

        else:
            print(json.dumps({"error": f"unknown command: {command}"}))
            return 1

    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"error": f"internal error: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
