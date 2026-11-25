# EPL Tactical Lab — Claude Code project rules

## Project goal
Build a reproducible, portfolio-ready Streamlit web app for EPL 2025/26 using real OpenPlay event data. Scope is based on the user's assignment document and the repository's existing `AGENTS.md`, `README.md`, `docs/requirements.md`, and data contracts. Preserve previous working code and tests. Submission target in the assignment: 2026-12-07.

## Required MVP — exactly three features
1. Team/match passing: team + match filters, actual pass start/end points, directional distributions, basic progressive passes.
2. xT analysis: verified public xT grid (or explicitly documented valid replacement), xT changes for eligible passes, team aggregates, xT heatmaps.
3. Player comparison: filter-consistent 2-player pass/xT comparisons, rankings, graceful missing-player handling.
Optional only after all required gates pass: filtered CSV download, evidence-based scouting summaries.
Excluded: login, billing, live 2026/27 event ingestion, invented pass receivers or fabricated pass networks, groundless predictions.

## Data and truthfulness constraints
- Analysis dataset is **EPL 2025/26**, never mix with separately archived 2026/27 results.
- OpenPlay release `events_eng_2526.parquet` is a public source. Do not add large raw/processed data to Git without permission. Run or improve the existing reproducible downloader, verify checksums, and record source/license in docs. Respect `.gitignore`.
- Previous Codex session **reported** 380 matches, 362,739 passes, and 32 pytest tests passing. Re-measure on the current checkout; never present those as freshly verified until rerun.
- Verify event schema, duplicates, nulls, pitch coordinate range, team/season filters, pass success, direction of play and event coverage before scoring.
- Never make up missing event rows, xT values, receiver identities, player minutes, or numerical results. No fabricated pass-receiver network. Without verified minutes, do not display per-90 metrics.
- xT calculations must document grid provenance, pitch normalization, action eligibility, signed value changes, missing/out-of-bound handling, and unit-testable examples. A reused model is NOT a trained original model and xT is not automatically a win-probability prediction.
- No EPL/club logos, photographs, or broadcast footage without usage rights; no secrets or token values in the repository.

## Harness workflow
0. Read the repository first. Source priority: assignment brief > `AGENTS.md`/docs > repository code > user instruction; identify and ask about material conflicts. Read the actual code before claiming its state.
1. PLAN: give a concise file-by-file plan, risk list, and acceptance tests; DO NOT edit source code until plan is approved when asked in Plan mode.
2. IMPLEMENT: do one small feature or bug fix per batch, minimize unrelated changes, respect existing interfaces.
3. VERIFY: run focused unit tests then `python -m pytest -q`; if possible run `streamlit run app.py` and smoke-test the UI. If tools/network unavailable, record the exact blockers and instructions; never pretend execution succeeded.
4. REVIEW: inspect changed files for data leakage, metric correctness, UI failure/empty states, and regression. Do not delete or weaken tests merely to make the suite green.
5. REPORT: at the end of each batch state modified files, commands run, actual outputs, passed/failed/skipped tests, known limitations, and recommended next smallest task. Keep `docs/claude_harness_plan.md` updated.
6. VERSION CONTROL: create reviewable changes and a PR if connected and authorized; never auto-merge to main or overwrite user work without approval.

## Definition of done
- Team/match filters change actual pass charts and stats consistently.
- Verified eligible successful passes yield independently reproducible xT totals and visualizations.
- Comparing two players uses the same filters; missing data handled without crashes.
- All existing and new tests pass; UI can start or every blocker is explicit; README provides reproducible setup, run and data-provenance instructions.
- `docs/claude_harness_plan.md` records feature status with evidence. Deliver a demonstration path: select team -> match -> passing pitch -> xT -> two-player comparison.
