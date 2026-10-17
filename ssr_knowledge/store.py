from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError, validate


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


def _validate_records(records: list[dict[str, Any]]) -> None:
    if not isinstance(records, list) or not records:
        raise ContractError("at least one knowledge record is required")
    for index, record in enumerate(records):
        try:
            validate(record, "record.schema.json")
        except ContractError as exc:
            raise ContractError(f"records[{index}]: {exc}") from exc
        for field in ("record_id", "topic", "summary"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ContractError(f"records[{index}].{field} must not be empty")
        source = record.get("source", {})
        for field in ("source_id", "source_type", "title", "locator", "accessed_at"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ContractError(f"records[{index}].source.{field} must not be empty")


def _records_digest(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
        self.research_dir = self.root / "research"
        self.published_dir = self.root / "published"
        self.tool_config_dir = self.root / "tool-configs"
        self.audit_path = self.root / "audit.jsonl"

    def _audit(self, record: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def candidate_path(self, candidate_id: str) -> Path:
        if not ID_PATTERN.fullmatch(candidate_id):
            raise ContractError("invalid candidate ID")
        return self.candidate_dir / f"{candidate_id}.json"

    def research_path(self, research_id: str) -> Path:
        if not ID_PATTERN.fullmatch(research_id):
            raise ContractError("invalid research ID")
        return self.research_dir / f"{research_id}.json"

    def tool_config_path(self, version: str) -> Path:
        if not VERSION_PATTERN.fullmatch(version):
            raise ContractError("tool config version must look like v1.2.3")
        return self.tool_config_dir / f"{version}.json"

    @staticmethod
    def validate_tool_config(config: dict[str, Any]) -> None:
        validate(config, "tool-config.schema.json")
        if not config["tools"]:
            raise ContractError("tool config must include at least one adapter")
        names = [tool["name"] for tool in config["tools"]]
        if len(names) != len(set(names)):
            raise ContractError("tool config adapter names must be unique")
        for tool in config["tools"]:
            parameter_names = [parameter["name"] for parameter in tool["parameters"]]
            if len(parameter_names) != len(set(parameter_names)):
                raise ContractError(f"tool config parameters must be unique: {tool['name']}")

    def save_tool_config(self, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_tool_config(config)
        version = config["config_version"]
        path = self.tool_config_path(version)
        if path.exists():
            raise ContractError("tool config version already exists")
        _write_json(path, config)
        self._audit({"event": "tool_config_saved", "version": version, "at": utc_now()})
        return config

    def load_tool_config(self, version: str) -> dict[str, Any]:
        path = self.tool_config_path(version)
        if not path.exists():
            raise ContractError("tool config version not found")
        config = json.loads(path.read_text(encoding="utf-8"))
        self.validate_tool_config(config)
        if config["config_version"] != version:
            raise ContractError("tool config file version does not match requested version")
        return config

    def save_research_packet(self, packet: dict[str, Any]) -> None:
        validate(packet, "research-packet.schema.json")
        if not packet["gaps"]:
            raise ContractError("research packet must include at least one gap")
        _validate_records(packet["records"])
        gap_ids = {gap["gap_id"] for gap in packet["gaps"]}
        if len(gap_ids) != len(packet["gaps"]):
            raise ContractError("research packet gap IDs must be unique")
        if {record.get("gap_id") for record in packet["records"]} != gap_ids:
            raise ContractError("research records must cover exactly the packet gaps")
        purpose_by_gap = {gap["gap_id"]: gap["purpose"] for gap in packet["gaps"]}
        if any(record["kind"] != purpose_by_gap[record["gap_id"]] for record in packet["records"]):
            raise ContractError("research record kind must match its gap purpose")
        path = self.research_path(packet["research_id"])
        if path.exists():
            raise ContractError("research packet already exists")
        _write_json(path, packet)
        self._audit({"event": "research_packet_created", "research_id": packet["research_id"], "at": utc_now()})

    def load_research_packet(self, research_id: str) -> dict[str, Any]:
        path = self.research_path(research_id)
        if not path.exists():
            raise ContractError("research packet not found")
        packet = json.loads(path.read_text(encoding="utf-8"))
        validate(packet, "research-packet.schema.json")
        if not packet["gaps"]:
            raise ContractError("research packet must include at least one gap")
        _validate_records(packet["records"])
        gap_ids = {gap["gap_id"] for gap in packet["gaps"]}
        if len(gap_ids) != len(packet["gaps"]):
            raise ContractError("research packet gap IDs must be unique")
        if {record.get("gap_id") for record in packet["records"]} != gap_ids:
            raise ContractError("research records must cover exactly the packet gaps")
        purpose_by_gap = {gap["gap_id"]: gap["purpose"] for gap in packet["gaps"]}
        if any(record["kind"] != purpose_by_gap[record["gap_id"]] for record in packet["records"]):
            raise ContractError("research record kind must match its gap purpose")
        return packet

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
            "publication_status": "published",
            "version": version,
            "candidate_id": candidate_id,
            "published_at": utc_now(),
            "records": candidate["records"],
            "records_sha256": _records_digest(candidate["records"]),
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
        if bundle["records_sha256"] != _records_digest(bundle["records"]):
            raise ContractError("published bundle records digest mismatch")
        return bundle
