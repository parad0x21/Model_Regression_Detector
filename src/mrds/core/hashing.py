"""Content hashing utilities.

Prompt and dataset *identity* is the hash of their content (not their filename),
so renaming a file does not change its identity but editing content does. These
helpers produce stable, deterministic SHA-256 digests.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    """Return the hex SHA-256 digest of a string (UTF-8 encoded)."""
    return hash_bytes(text.encode("utf-8"))


def hash_json(obj: Any) -> str:
    """Return a deterministic hex SHA-256 digest of a JSON-serialisable object.

    Keys are sorted and separators are normalised so that semantically equal
    objects hash identically regardless of key ordering or whitespace.
    """
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hash_text(canonical)
