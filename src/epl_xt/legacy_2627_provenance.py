"""Archived, no longer used by 2025/26 analytics UI."""
"""Explicit provenance gate; a user must approve the source before analysis."""
import json
from pathlib import Path

MANDATORY = ("provider", "source_reference", "license_or_permission", "event_coordinate_mapping", "attacking_direction_rule", "xt_grid_source", "retrieved_on")


def read_approved_manifest(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise ValueError("Missing config/source_manifest.json; copy example and get user approval")
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid source manifest JSON") from exc
    if manifest.get("verified_by_user") is not True:
        raise ValueError("Source manifest is not explicitly approved by the user")
    if manifest.get("competition") != "EPL" or manifest.get("season") != "2026/27":
        raise ValueError("Approved source must match EPL 2026/27; no silent season substitution")
    for key in MANDATORY:
        if not isinstance(manifest.get(key), str) or not manifest[key].strip() or "NOT VERIFIED" in manifest[key].upper():
            raise ValueError(f"Missing or unverified manifest field: {key}")
    if not isinstance(manifest.get("match_ids"), list) or not manifest["match_ids"] or not all(isinstance(i, str) and i.strip() for i in manifest["match_ids"]):
        raise ValueError("Approved manifest must list actual match IDs")
    return manifest
