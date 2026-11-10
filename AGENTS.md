# Codex project agent rules — EPL 2025/26 (OpenPlay)

## Authorized project decision (2026-11-09)
User asked to keep EPL 2026/27 only if verified pass events were obtainable, otherwise switch to 2025/26. No verified open 2026/27 player/pass-coordinate dataset was found. **The tactical dashboard season is therefore 2025/26.** The 2026/27 match scores are kept on a separate archival page only.

## Sources & limits
- Actual openplay (Noah Bair), release data-v0.1.0, `events_eng_2526.parquet` (~11.5 MB) from https://github.com/nlbair/openplay/releases/tag/data-v0.1.0
- Dataset CC BY 4.0: credit "openplay (Noah Bair)". Original publisher documents source-native 0..100 pitch coords, every team attacks toward x=100.
- The dataset **does not document a recipient column**. `recipient` is left null and exact passer-to-recipient edges must NOT be claimed. Conservative inferred edges only as explicitly labeled separate functionality after measured validation.
- xT grid: Karun Singh's `open_xt_12x8_v1.json`, an older published EPL model; not trained on 2025/26.
- Do not make up xT, matches, recipients, player names or coordinates. No season conflation.

## Workflow
1. Read `docs/data_sources.md`, `docs/data_contract.md`, `docs/requirements.md`.
2. For data download run `python scripts/download_openplay_2526.py` on a network-connected PC. This script hashes source assets against the publisher's SHA-256 file. Raw data stays untouched.
3. Conversion errors or checksum mismatches must stop, not create placeholder datasets.
4. Run `python -m pytest -q` after each change; report what was tested and what wasn't.
5. Keep output attribution, data coverage, selected matches, xT definition and missing recipients visible in the UI.
6. Only use `data/processed/passes.csv` for EPL 2025/26. Preserve result-only 26/27 material without merging seasons.
7. Avoid destructive operations, fabricated tests posed as real data, secrets, and undocumented dependencies.
8. `verified_by_user=false` in generated manifest is accurate: this script verifies checksum integrity, not manual human source approval. Do not change this flag automatically.
