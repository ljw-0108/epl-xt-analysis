"""Revalidate local verified-source imports at dashboard startup."""
import hashlib
import json
from pathlib import Path

ALLOWED_SOURCE = "https://github.com/nlbair/openplay/releases/tag/data-v0.1.0"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_verified_import(manifest_path, passes_path, grid_path):
    try:
        m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("25/26 데이터 검증 파일이 없습니다. 다운로드 스크립트를 실행하세요") from exc
    if (m.get("competition"), m.get("season"), m.get("source_reference")) != ("EPL", "2025/26", ALLOWED_SOURCE):
        raise ValueError("시즌 또는 출처가 25/26 OpenPlay 원본과 다릅니다")
    if m.get("verification_method") != "source_release_sha256":
        raise ValueError("원본 SHA-256 검증 기록이 누락됐습니다")
    if not m.get("match_ids") or not isinstance(m["match_ids"], list):
        raise ValueError("경기 목록이 누락됐습니다")
    for path, key in ((passes_path, "processed_passes_sha256"), (grid_path, "xt_grid_sha256")):
        if not Path(path).is_file() or sha256(path) != m.get(key):
            raise ValueError(f"파일이 없거나 무결성 검증 실패: {path}")
    return m
