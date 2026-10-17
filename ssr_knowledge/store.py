from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError, validate


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


def _validate_records(records: list[dict[str, Any]]) -> None:
    for index, record in enumerate(records):
        try:
            validate(record, "record.schema.json")
        except ContractError as exc:
            raise ContractError(f"records[{index}]: {exc}") from exc


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class LocalKnowledgeStore:
    """File-backed candidate and published stores, private to this repo."""

    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir)
        self.candidate_dir = self.root / "candidates"
        self.published_dir = self.root / "published"
        self.audit_path = self.root / "audit.jsonl"

    def _audit(self, record: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def candidate_path(self, candidate_id: str) -> Path:
        if not ID_PATTERN.fullmatch(candidate_id):
            raise ContractError("invalid candidate ID")
        return self.candidate_dir / f"{candidate_id}.json"

    def save_candidate(self, candidate: dict[str, Any]) -> None:
        validate(candidate, "candidate.schema.json")
        _validate_records(candidate["records"])
        path = self.candidate_path(candidate["candidate_id"])
        if path.exists():
            raise ContractError("candidate already exists")
        _write_json(path, candidate)
        self._audit({"event": "candidate_created", "candidate_id": candidate["candidate_id"], "at": utc_now()})

    def load_candidate(self, candidate_id: str) -> dict[str, Any]:
        path = self.candidate_path(candidate_id)
        if not path.exists():
            raise ContractError("candidate not found")
        candidate = json.loads(path.read_text(encoding="utf-8"))
        validate(candidate, "candidate.schema.json")
        _validate_records(candidate["records"])
        return candidate

    def update_candidate(self, candidate: dict[str, Any], event: str) -> None:
        validate(candidate, "candidate.schema.json")
        _validate_records(candidate["records"])
        _write_json(self.candidate_path(candidate["candidate_id"]), candidate)
        self._audit({"event": event, "candidate_id": candidate["candidate_id"], "at": utc_now()})

    def publish(self, candidate_id: str, version: str) -> dict[str, Any]:
        if not VERSION_PATTERN.fullmatch(version):
            raise ContractError("version must look like v1.2.3")
        candidate = self.load_candidate(candidate_id)
        if candidate["status"] != "approved":
            raise ContractError("only an approved candidate may be published")
        target = self.published_dir / f"{version}.json"
        if target.exists():
            raise ContractError("published version already exists")
        bundle = {
            "version": version,
            "candidate_id": candidate_id,
            "published_at": utc_now(),
            "records": candidate["records"],
        }
        validate(bundle, "published-bundle.schema.json")
        _validate_records(bundle["records"])
        _write_json(target, bundle)
        candidate["status"] = "published"
        self.update_candidate(candidate, "candidate_published")
        return bundle

    def read_published(self, version: str) -> dict[str, Any]:
        if not VERSION_PATTERN.fullmatch(version):
            raise ContractError("version must look like v1.2.3")
        path = self.published_dir / f"{version}.json"
        if not path.exists():
            raise ContractError("published version not found")
        bundle = json.loads(path.read_text(encoding="utf-8"))
        validate(bundle, "published-bundle.schema.json")
        _validate_records(bundle["records"])
        return bundle
