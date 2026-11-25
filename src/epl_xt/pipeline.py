"""Download -> checksum -> convert pipeline for OpenPlay EPL 2025/26 (used by the CLI script and the app).

Order matters: any existing manifest is removed first and the new one is written last, so a
failed run can never leave a manifest that vouches for half-written files. A checksum
mismatch stops the run; nothing is imputed or substituted.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .openplay_adapter import SET_PIECE_FLAGS, convert_openplay_passes
from .provenance_2526 import ALLOWED_SOURCE, sha256
from .quality import match_index
from .validation import validate_passes

RELEASE = "https://github.com/nlbair/openplay/releases/download/data-v0.1.0"
EVENT_FILE = "events_eng_2526.parquet"
GRID_URL = "https://karun.in/blog/data/open_xt_12x8_v1.json"
# The grid publisher provides no checksum file. This SHA-256 was observed on 2026-11-25
# (see docs/data_quality_report.md); a different file stops the pipeline.
GRID_SHA256 = "5d8e9aaa1da23bbb39a6c6ffdd5b96d175e01c800064c5a1cc19e228c9875a7f"
SOURCE_COLUMNS = ["comp", "season", "match_id", "team", "player", "type", "outcome", "x", "y", "end_x", "end_y",
                  *SET_PIECE_FLAGS]

Fetcher = Callable[[str, Path, int], None]


def download(url: str, dest: Path, max_bytes: int) -> None:
    """Stream url to dest via a .part file; refuse files larger than max_bytes."""
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


def build_verified_dataset(root: str | Path, fetch: Fetcher = download, grid_sha256: str = GRID_SHA256,
                           log: Callable[[str], None] = lambda _msg: None) -> dict:
    """Create data/processed/* and config/source_manifest.json under root; return the manifest."""
    root = Path(root)
    raw, processed = root / "data/raw", root / "data/processed"
    manifest_path = root / "config/source_manifest.json"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.unlink(missing_ok=True)

    checksum_path = raw / "openplay_checksums.json"
    source_path = raw / EVENT_FILE
    grid_json_path = raw / "karun_open_xt_12x8_v1.json"

    log("OpenPlay 체크섬 파일 확인")
    fetch(f"{RELEASE}/checksums.json", checksum_path, 2_000_000)
    expected = json.loads(checksum_path.read_text(encoding="utf-8"))[EVENT_FILE]["sha256"]
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("Invalid source checksum")
    if not source_path.exists() or sha256(source_path) != expected:
        log("이벤트 원본 내려받기 (약 11.5MB)")
        fetch(f"{RELEASE}/{EVENT_FILE}", source_path, 80_000_000)
    if sha256(source_path) != expected:
        source_path.unlink(missing_ok=True)
        raise ValueError("Downloaded event data failed official SHA-256 verification")

    log("xT 그리드 확인")
    fetch(GRID_URL, grid_json_path, 50_000)
    if sha256(grid_json_path) != grid_sha256:
        raise ValueError("xT grid differs from the pinned SHA-256; review the source before using it")
    grid = np.asarray(json.loads(grid_json_path.read_text(encoding="utf-8")), dtype=float)
    if grid.shape != (8, 12) or not np.isfinite(grid).all() or np.any(grid < 0):
        raise ValueError("Karun xT grid must contain 8 x 12 finite nonnegative values")

    log("패스 변환 및 검증")
    # Base columns are required (the adapter rejects their absence); q_ flag columns vary by file.
    available = set(pq.read_schema(source_path).names)
    columns = [c for c in SOURCE_COLUMNS if c in available or c not in SET_PIECE_FLAGS]
    canonical, report = convert_openplay_passes(pd.read_parquet(source_path, columns=columns))
    canonical = validate_passes(canonical)
    passes_path = processed / "passes.csv"
    canonical.to_csv(passes_path, index=False, encoding="utf-8-sig")
    grid_path = processed / "xt_grid.csv"
    np.savetxt(grid_path, grid, delimiter=",", fmt="%.8f")
    matches_path = processed / "matches.csv"
    match_index(canonical).to_csv(matches_path, index=False, encoding="utf-8-sig")

    manifest = {
        "provider": "openplay (Noah Bair)", "source_reference": ALLOWED_SOURCE,
        "event_asset": f"{RELEASE}/{EVENT_FILE}", "event_asset_sha256": expected,
        "competition": "EPL", "season": "2025/26", "license_or_permission": "CC BY 4.0 — credit openplay (Noah Bair)",
        "verification_method": "source_release_sha256", "verified_by_user": False,
        "event_coordinate_mapping": "OpenPlay x,y,end_x,end_y native 0..100; no scaling",
        "attacking_direction_rule": "OpenPlay documented: each team attacks toward x=100",
        "recipient_field": "not provided; left blank; player-to-player network not claimed",
        "xt_grid_source": GRID_URL, "xt_grid_json_sha256": grid_sha256,
        "xt_grid_note": "Published model trained on EPL 2017/18, not refit to 2025/26",
        "retrieved_on": date.today().isoformat(),
        "match_ids": sorted(canonical["match_id"].unique().tolist()),
        "processed_passes_sha256": sha256(passes_path), "xt_grid_sha256": sha256(grid_path),
        "processed_matches_sha256": sha256(matches_path),
        "quality_report": report,
    }
    tmp = manifest_path.with_name(manifest_path.name + ".part")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(manifest_path)
    log(f"완료: {report['pass_rows']:,}개 패스, {report['matches_with_passes']}경기")
    return manifest
