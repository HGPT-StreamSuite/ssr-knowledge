"""Read one installed PEAK TextAsset; never launch, decrypt or rewrite the game."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .catalog import Catalog, canonical, digest, resolve_data_dir
from .contracts import ContractError
from .game_localization import parse_game_csv
from .store import utc_now
from .unity_stream import BoundedUnityFS, BundleWindow


def file_sha256(path: Path) -> str:
    hash_ = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hash_.update(chunk)
    return hash_.hexdigest()


def extract_installed_text(game_dir: str, output_dir: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version("UnityPy")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ContractError("uv sync --group extraction is required; no automatic installation") from exc
    if version != "1.25.4":
        raise ContractError("expected locked UnityPy 1.25.4")
    root = Path(game_dir).resolve()
    manifest = root.parent.parent / "appmanifest_3527290.acf"
    if not manifest.is_file() or not (root / "PEAK.exe").is_file():
        raise ContractError("expected an existing PEAK Steam installation")
    fields = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', manifest.read_text(encoding="utf-8-sig")))
    if fields.get("appid") != "3527290" or fields.get("installdir") != root.name or not re.fullmatch(r"\d+", fields.get("buildid", "")):
        raise ContractError("PEAK manifest/path mismatch")
    version_bytes = (root / "version.txt").read_bytes()
    if not 1 <= len(version_bytes) <= 512:
        raise ContractError("invalid game version text")
    game_version = version_bytes.decode("utf-8-sig").splitlines()[0]
    output = resolve_data_dir(output_dir)
    existing = output
    while not existing.exists(): existing = existing.parent
    if shutil.disk_usage(existing).free < 50 * 1024 * 1024:
        raise ContractError("at least 50 MiB free disk required")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "localization.txt").exists() or (output / "receipt.json").exists():
        raise ContractError("use a fresh extraction output folder; existing evidence is preserved")
    path = root / "PEAK_Data" / "data.unity3d"
    before = file_sha256(path)
    from UnityPy.files.SerializedFile import SerializedFile
    from UnityPy.streams import EndianBinaryReader
    from UnityPy.helpers import TypeTreeHelper
    TypeTreeHelper.read_typetree_boost = False
    bundle = BoundedUnityFS(path)
    try:
        nodes = [n for n in bundle.nodes if n["name"] == "resources.assets" and n["flags"] & 4]
        if len(nodes) != 1 or nodes[0]["size"] > 128 * 1024 * 1024:
            raise ContractError("expected one bounded resources.assets node")
        asset = SerializedFile(EndianBinaryReader(BundleWindow(bundle, nodes[0])), name="resources.assets")
        objects = [o for o in asset.objects.values() if o.type.name == "TextAsset" and o.byte_size <= 2_000_000 and o.peek_name() == "Localized_Text"]
        if len(objects) != 1:
            raise ContractError("Localized_Text must identify exactly one TextAsset")
        obj = objects[0]
        raw = obj.parse_as_object().m_Script.encode("utf-8", "surrogateescape")
        parsed = parse_game_csv(raw.decode("utf-8-sig", errors="strict"))
        after = file_sha256(path)
        if before != after or version_bytes != (root / "version.txt").read_bytes():
            raise ContractError("game changed during extraction; discard this observation")
        receipt = {"schema_version": 1, "game": "PEAK:3527290", "game_version": game_version,
            "game_version_text": version_bytes.decode("utf-8-sig"), "steam_build_id": fields["buildid"], "game_root": str(root),
            "bundle_path": str(path), "bundle_bytes": path.stat().st_size, "bundle_sha256_before": before, "bundle_sha256_after": after,
            "asset": "resources.assets", "text_asset_name": "Localized_Text", "path_id": obj.path_id, "object_byte_start": obj.byte_start,
            "object_byte_size": obj.byte_size, "raw_sha256": digest(raw), "text_bytes": len(raw), "columns": parsed["columns"], "header": parsed["header"],
            "unity_version": bundle.engine, "tool": "UnityPy", "tool_version": version, "extracted_at": utc_now(),
            "read_stats": {"compressed_data_read_bytes": bundle.read_bytes, "compressed_index_read_bytes": bundle.index_compressed_bytes,
                           "decompressed_data_bytes": bundle.decompressed_bytes, "max_cache_bytes": bundle.max_cache,
                           "streaming_hash_passes": 2, "streaming_hash_read_bytes": 2 * path.stat().st_size},
            "scope": "One official installed TextAsset only; no game launch, asset writes, textures, scene scans, archive copies or decryption."}
        (output / "localization.txt").write_bytes(raw)
        (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"state": "extracted", "file": str(output / "localization.txt"), "receipt": str(output / "receipt.json"),
                "raw_sha256": digest(raw), "columns": parsed["columns"], "read_stats": receipt["read_stats"], "game_version": game_version}
    finally:
        bundle.file.close()


def import_game_text(store: Catalog, file: str, receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1 or receipt.get("game") != "PEAK:3527290":
        raise ContractError("invalid installed game extraction receipt")
    path = Path(file)
    if not path.is_file() or not 1 <= path.stat().st_size <= 2_000_000:
        raise ContractError("bounded extracted text required")
    raw = path.read_bytes()
    parsed = parse_game_csv(raw.decode("utf-8-sig", errors="strict"))
    if any(not isinstance(receipt.get(k), str) or not receipt[k].strip() for k in ("game_version", "steam_build_id", "extracted_at")):
        raise ContractError("game version/build/extraction time must be explicit text")
    if (digest(raw) != receipt.get("raw_sha256") or parsed["columns"] != receipt.get("columns") or parsed["header"] != receipt.get("header")
            or receipt.get("bundle_sha256_before") != receipt.get("bundle_sha256_after")
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("bundle_sha256_before", "")))
            or receipt.get("asset") != "resources.assets" or receipt.get("text_asset_name") != "Localized_Text"
            or not re.fullmatch(r"\d+", str(receipt.get("steam_build_id", "")))):
        raise ContractError("game extraction hash/header/column/provenance mismatch")
    uses = {purpose: {"status": "allowed" if purpose in {"local_cache", "search_index"} else "unknown",
                     "basis": "Explicit user authorization for private local extraction/name lookup only; no redistribution/model input/training license asserted."}
            for purpose in ("local_cache", "search_index", "ai_input", "ai_train")}
    results = {}
    for locale in ("en", "zh-TW"):
        source = {"source_id": "peak-game-text-" + receipt["steam_build_id"] + "-" + locale.lower() + "-" + digest(raw)[:12],
            "url": "installed-game-text:3527290:" + receipt["steam_build_id"] + ":" + digest(raw) + ":" + locale,
            "original_url": "https://store.steampowered.com/app/3527290/PEAK/", "source_type": "official",
            "title": "PEAK installed game item strings (" + locale + ")", "language": locale,
            "declared_version": receipt["game_version"] + "; Steam build " + receipt["steam_build_id"], "selector": {"tag": "body"}, "interval_seconds": 3,
            "acquisition": {"kind": "installed_game_text"},
            "policy": {"allow_fetch": False, "allow_import": True, "reviewed_at": receipt["extracted_at"], "terms_url": "https://store.steampowered.com/app/3527290/PEAK/",
                       "notes": "Copyright game rights holders. User-authorized private name reference only, no resource redistribution permission asserted.", "uses": uses}}
        existing_source = store.db.execute("SELECT url,config_json FROM sources WHERE source_id=?", (source["source_id"],)).fetchone()
        if existing_source and existing_source["url"] == source["url"]:
            # A new observation time alone is not a changed source permission.
            source["policy"]["reviewed_at"] = json.loads(existing_source["config_json"])["policy"]["reviewed_at"]
        body = canonical({"schema_version": 1, "locale": locale, "conflicting_keys": parsed["conflicting_keys"], "items": [{"key": r["key"], "en": r["en"], "text": r[locale], "csv_records": r["csv_records"]} for r in parsed["items"]]})
        metadata = {"acquisition_kind": "installed_game_text", "receipt": receipt, "imported_at": utc_now(), "extractor_version": "peak-game-text-v1",
            "name_evidence": {"kind": "game_ui", "locale": locale}, "requested_url": None, "canonical_url": source["url"],
            "canonical_basis": "Installed official resource/key; Steam link is attribution only, not an HTTP acquisition", "source_updated_at": None,
            "source_updated_basis": "unknown; installed version/build and file hashes retained separately", "body_locator": {"format": "game_item_names_json", "asset": receipt["asset"], "path_id": receipt["path_id"]},
            "collector_called_llm": False, "http_requests": 0}
        store.register_source(source)
        results[locale] = store.save_snapshot(source, raw, body, metadata)
    store.event(None, "game_text_import", {"results": results, "http_requests": 0, "observed_extracted_at": receipt["extracted_at"], "raw_sha256": digest(raw)})
    return {"results": results, "columns": parsed["columns"], "conflicting_keys": parsed["conflicting_keys"], "http_requests": 0}
