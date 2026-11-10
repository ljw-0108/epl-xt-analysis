import json
import hashlib
import pytest
from epl_xt.provenance_2526 import read_verified_import, ALLOWED_SOURCE


def test_verified_import_checks_hashes_and_season(tmp_path):
    passes = tmp_path / "passes.csv"
    grid = tmp_path / "xt_grid.csv"
    passes.write_text("A", encoding="utf-8")
    grid.write_text("B", encoding="utf-8")
    manifest = tmp_path / "source_manifest.json"
    data = dict(competition="EPL",season="2025/26",source_reference=ALLOWED_SOURCE,
                verification_method="source_release_sha256",match_ids=["1"],
                processed_passes_sha256=hashlib.sha256(b"A").hexdigest(),
                xt_grid_sha256=hashlib.sha256(b"B").hexdigest())
    manifest.write_text(json.dumps(data),encoding="utf-8")
    assert read_verified_import(manifest, passes, grid)["season"] == "2025/26"
    passes.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="무결성"):
        read_verified_import(manifest, passes, grid)


def test_wrong_season_rejected(tmp_path):
    p=tmp_path/"m.json"
    p.write_text(json.dumps({"competition":"EPL","season":"2026/27","source_reference":ALLOWED_SOURCE}),encoding="utf-8")
    with pytest.raises(ValueError,match="시즌"):
        read_verified_import(p,tmp_path/"passes",tmp_path/"grid")
