# Canonical 2025/26 EPL pass-event contract

`data/processed/passes.csv` :
- `match_id`, `team`, `player`, `recipient`, `x`, `y`, `end_x`, `end_y`, `is_successful`
- Event data: **OpenPlay** `events_eng_2526.parquet`; ensure `comp=eng`, `season=2526`, `type=Pass`.
- `is_successful`: OpenPlay `outcome == Successful`.
- `x`, `y`, `end_x`, `end_y`: native OpenPlay 0..100, each team attacks toward x=100. Remove & count rows with missing or out-of-bounds coords; never impute values.
- `recipient`: left null. OpenPlay public event dictionary does **not** list a reliable recipient field. No exact pairwise connections can be claimed.
- Match ids and sha256 hashes are recorded after verified download in `config/source_manifest.json`. `verified_by_user=false` signals automatic checksum verification is **not** human review.
- 8×12 xT grid: Karun Singh open_xt_12x8_v1.json (older EPL baseline); not calibrated on 25/26.
- xT: for successful pass, `xT(end)-xT(start)`; failed pass value=0, signed result retained. This is a **pass-only** xT contribution metric.
- 26/27 result-only data is separate from 25/26 pass analytics and cannot be merged.
