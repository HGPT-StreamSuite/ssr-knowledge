from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"


class ContractError(ValueError):
    pass


def load_schema(name: str) -> dict[str, Any]:
    with (CONTRACTS / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ContractError(f"unsupported schema type: {expected}")


def _validate(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected and not (
        any(_is_type(value, option) for option in expected)
        if isinstance(expected, list)
        else _is_type(value, expected)
    ):
        return [f"{path}: expected {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is outside enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(_validate(item, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: additional property is not allowed")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(_validate(item, schema["items"], f"{path}[{index}]"))
    return errors


def validate(value: Any, schema_name: str) -> None:
    errors = _validate(value, load_schema(schema_name), "$")
    if errors:
        raise ContractError("; ".join(errors))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
