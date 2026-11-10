# 소스 점검 — 2026-11-09

## 2026/27 EPL — 패스 이벤트 사용 불가
- 2026/27 결과표 1~10라운드 100경기(보관): `data/raw/epl_2627_rounds_1_10_results.csv`.
- 선수별 패스 좌표 및 수신자 정보가 포함된 라이선스가 명확한 무료 2026/27 시즌 원본을 확인하지 못함. "없다"는 절대적 증명이 아니라 공개 확인 범위의 결론.
- https://github.com/oladeeayo/open-matchday — 결과/일부 슈팅·코너 등, 패스 이벤트 없음.
- https://github.com/nlbair/openplay — 2025/26까지, 2026/27 미포함.

## 분석 범위: 2025/26 EPL (공개 이벤트 원본 확인)
- source: openplay (Noah Bair), data-v0.1.0 (released 2026-11-03)
- release: https://github.com/nlbair/openplay/releases/tag/data-v0.1.0
- single-season asset: https://github.com/nlbair/openplay/releases/download/data-v0.1.0/events_eng_2526.parquet
- 11,531,896 bytes (~11.5MB) per public release metadata; **script must download & verify SHA256**.
- file type: Parquet; source has match_id/team/player/type/outcome/x/y/end_x/end_y, normalized 0..100 and opponent goal toward x100. Columns documented: https://github.com/nlbair/openplay/blob/main/DATA_DICTIONARY.md
- `recipient` **not directly provided** in documented event schema. Do NOT claim exact pairwise connections.
- license: Creative Commons Attribution 4.0, credit "openplay (Noah Bair)" (see repo README/LICENSE).
- Data is a static snapshot with known missing/problem matches, so check source `coverage.csv`, `known_gaps.csv`, `data_issues.csv` if extending scope. No pretense of perfect coverage.
- import status: **Not run inside ChatGPT environment** (network unavailable). Fetch on user PC using script. An automatically produced `config/source_manifest.json` records real match_ids and hashes after download.

## xT surface (do not claim refitted for 2025/26)
- Source: Karun Singh, `https://karun.in/blog/data/open_xt_12x8_v1.json`.
- Literature: https://socceraction.readthedocs.io/en/latest/documentation/intro.html
- Model derived from older 2017/18 EPL analysis, xT(x,y) used at 12 cols × 8 rows.
- Metric: signed pass-only xT delta for successful passes; attempted/failed passes contribute 0 by project definition.

## Seasons must NEVER be joined
2026/27 scores are independent archival context; 25/26 player/pass tactics are the current project analytics.
