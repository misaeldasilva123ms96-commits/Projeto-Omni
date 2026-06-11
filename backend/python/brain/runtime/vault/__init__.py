"""Read-only access helpers for governed vault Markdown notes."""

from .vault_reader import list_vault_notes, read_vault_note, search_vault_notes
from .vault_types import VaultReadResult

__all__ = [
    "VaultReadResult",
    "list_vault_notes",
    "read_vault_note",
    "search_vault_notes",
]
