"""Download only one EPL 2025/26 event file, check publisher SHA256, convert passes.

Run: python scripts/download_openplay_2526.py
Internet is required on the machine executing this command.
The pipeline itself lives in src/epl_xt/pipeline.py so the app can run the same steps.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epl_xt.pipeline import EVENT_FILE, build_verified_dataset  # noqa: E402


def main():
    manifest = build_verified_dataset(ROOT, log=print)
    report = manifest["quality_report"]
    print("Verified OpenPlay release:", ROOT / "data/raw" / EVENT_FILE, "sha256", manifest["event_asset_sha256"])
    print("Saved", report["pass_rows"], "real EPL 2025/26 passes over", report["matches_with_passes"], "matches")
    print("Dropped invalid pass rows:", report["dropped_pass_rows"])
    print("Recipient is missing; no verified player-to-player pass network is implied")
    print("Saved data/processed/{passes,xt_grid,matches}.csv and config/source_manifest.json")


if __name__ == "__main__":
    main()
