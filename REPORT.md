# REPORT.md — PR #1 (Small tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1  
**Branch:** `develop-1` → `main`  
**Code SHA:** `c82a6cf1` · **Δ:** +93 / −8  

> Collated analysis (how Greptile/Copilot work, graph hops, buy decision): see **`develop-3`**  
> [`GREPTILE_DIFFERENTIAL_CODE_REPORT.md`](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/blob/develop-3/GREPTILE_DIFFERENTIAL_CODE_REPORT.md).  
> **“Copilot” in that report = Cursor Bugbot** (GitHub Copilot unavailable).

## What changed
- `main.py`: bare `BLE`; absolute resume path  
- `mutations.py`: dictionary insert, splice, strategy hits  
- `simple_fuzzer2.py`: crash-hot havoc bias; occasional same-path splice  

## Greptile
Confidence **5/5**. Accurate summary of mutations + BLE CLI. No inline defects. Contract-aware note on resume path vs harness.

## Copilot (Cursor)
**0 bugs** — aligned.

## Graph value on this tier
Low. Clean small PR; neither inventing defects. Greptile’s extras = confidence score narrative.

## Verdict
Tie / low ROI for paid Greptile alone on <100 LOC clean changes.
