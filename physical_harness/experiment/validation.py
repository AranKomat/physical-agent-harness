"""Strict boundary helpers. Unknown metadata and non-finite JSON are rejected."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


def dumps(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def loads(value: str | bytes) -> Any:
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = item
        return result

    def reject(value):
        raise ValueError(f"Non-finite JSON constant: {value}")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=reject)


def digest(value: Any) -> str:
    return hashlib.sha256(dumps(value)).hexdigest()


def text(value: Any, name: str = "text", maximum: int = 8192) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > maximum:
        raise ValueError(f"{name} must be nonempty bounded text")
    return value


def number(value: Any, name: str = "number", minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return float(value)


def integer(value: Any, name: str = "integer", minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def fields(value: Any, required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(value, Mapping) or not required <= set(value) <= required | optional:
        raise ValueError(f"Expected fields {sorted(required)}, optional {sorted(optional)}")


def identifiers(values: Any, maximum: int = 64) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or len(values) > maximum:
        raise ValueError("Expected bounded identifier list")
    result = tuple(text(x, "identifier", 256) for x in values)
    if len(set(result)) != len(result):
        raise ValueError("Duplicate identifiers")
    return result


def validate_schema(value: Any, schema: dict) -> None:
    """Validate locally even when a provider advertises strict structured output."""
    from jsonschema import Draft202012Validator
    Draft202012Validator(schema).validate(value)
