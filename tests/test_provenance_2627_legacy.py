import json
import pytest
from epl_xt.legacy_2627_provenance import read_approved_manifest


def test_manifest_missing_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="Missing"):
        read_approved_manifest(tmp_path / "none.json")


def test_unapproved_manifest_rejected(tmp_path):
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps({"competition": "EPL", "season": "2026/27", "verified_by_user": False}))
    with pytest.raises(ValueError, match="not explicitly approved"):
        read_approved_manifest(path)


def test_approved_manifest(tmp_path):
    manifest = dict(provider="provider", source_reference="dataset id", license_or_permission="approved for research", competition="EPL", season="2026/27", match_ids=["m1"], event_coordinate_mapping="source 120x80 -> 0..100", attacking_direction_rule="verified event metadata", xt_grid_source="documented grid version", retrieved_on="2026-11-09", verified_by_user=True)
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(manifest))
    assert read_approved_manifest(path)["match_ids"] == ["m1"]
