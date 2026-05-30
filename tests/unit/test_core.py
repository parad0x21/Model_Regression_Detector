"""Tests for core foundation utilities (ids + hashing)."""

from __future__ import annotations

from mrds.core.hashing import hash_json, hash_text
from mrds.core.ids import new_run_id


def test_run_ids_are_unique_hex() -> None:
    a, b = new_run_id(), new_run_id()
    assert a != b
    assert len(a) == 32
    int(a, 16)  # raises if not valid hex


def test_hash_text_is_deterministic() -> None:
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("hello") != hash_text("world")


def test_hash_json_is_key_order_independent() -> None:
    assert hash_json({"a": 1, "b": 2}) == hash_json({"b": 2, "a": 1})
    assert hash_json({"a": 1}) != hash_json({"a": 2})
