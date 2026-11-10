"""Download only one EPL 2025/26 event file, check publisher SHA256, convert passes.

Run: python scripts/download_openplay_2526.py
Internet is required on the machine executing this command.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.openplay_adapter import convert_openplay_passes
from epl_xt.provenance_2526 import sha256, ALLOWED_SOURCE
from epl_xt.validation import validate_passes

RELEASE = "https://github.com/nlbair/openplay/releases/download/data-v0.1.0"
EVENT_FILE = "events_eng_2526.parquet"
GRID_URL = "https://karun.in/blog/data/open_xt_12x8_v1.json"
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"


def download(url: str, dest: Path, max_bytes: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    size = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "epl-xt-student-research/1.0"})
        with urllib.request.urlopen(req, timeout=180) as r, part.open("wb") as f:
            while block := r.read(1 << 20):
                size += len(block)
                if size > max_bytes:
                    raise ValueError(f"Source file too large: {url}")
                f.write(block)
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    checksum_path = RAW / "openplay_checksums.json"
    source_path = RAW / EVENT_FILE
    grid_json_path = RAW / "karun_open_xt_12x8_v1.json"
    download(f"{RELEASE}/checksums.json", checksum_path, 2_000_000)
    checksums = json.loads(checksum_path.read_text(encoding="utf-8"))
    expected = checksums[EVENT_FILE]["sha256"]
    if len(expected) != 64:
        raise ValueError("Invalid source checksum")
    if not source_path.exists() or sha256(source_path) != expected:
        download(f"{RELEASE}/{EVENT_FILE}", source_path, 80_000_000)
    if sha256(source_path) != expected:
        source_path.unlink(missing_ok=True)
        raise ValueError("Downloaded event data failed official SHA-256 verification")
    columns = ["comp", "season", "match_id", "team", "player", "type", "outcome", "x", "y", "end_x", "end_y"]
    source_events = pd.read_parquet(source_path, columns=columns)
    canonical, report = convert_openplay_passes(source_events)
    canonical = validate_passes(canonical)
    passes_path = PROCESSED / "passes.csv"
    canonical.to_csv(passes_path, index=False, encoding="utf-8-sig")
    download(GRID_URL, grid_json_path, 50_000)
    grid = np.asarray(json.loads(grid_json_path.read_text(encoding="utf-8")), dtype=float)
    if grid.shape != (8, 12) or not np.isfinite(grid).all() or np.any(grid < 0):
        raise ValueError("Karun xT grid must contain 8 x 12 finite nonnegative values")
    grid_path = PROCESSED / "xt_grid.csv"
    np.savetxt(grid_path, grid, delimiter=",", fmt="%.8f")
    manifest = {
        "provider": "openplay (Noah Bair)", "source_reference": ALLOWED_SOURCE,
        "event_asset": f"{RELEASE}/{EVENT_FILE}", "event_asset_sha256": expected,
        "competition": "EPL", "season": "2025/26", "license_or_permission": "CC BY 4.0 — credit openplay (Noah Bair)",
        "verification_method": "source_release_sha256", "verified_by_user": False,
        "event_coordinate_mapping": "OpenPlay x,y,end_x,end_y native 0..100; no scaling",
        "attacking_direction_rule": "OpenPlay documented: each team attacks toward x=100",
        "recipient_field": "not provided; left blank; player-to-player network not claimed",
        "xt_grid_source": GRID_URL,
        "xt_grid_note": "Published model trained on EPL 2017/18, not refit to 2025/26",
        "retrieved_on": date.today().isoformat(),
        "match_ids": sorted(canonical["match_id"].unique().tolist()),
        "processed_passes_sha256": sha256(passes_path), "xt_grid_sha256": sha256(grid_path),
        "quality_report": report,
    }
    manifest_path = ROOT / "config/source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified OpenPlay release:", source_path, "sha256", expected)
    print("Saved", len(canonical), "real EPL 2025/26 passes over", canonical.match_id.nunique(), "matches")
    print("Dropped invalid pass rows:", report["dropped_pass_rows"])
    print("Recipient is missing; no verified player-to-player pass network is implied")
    print("Saved", passes_path, grid_path, manifest_path)


if __name__ == "__main__":
    main()
