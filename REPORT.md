# REPORT.md — PR #1 (Small tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1  
**Branch:** `develop-1` → `main`  
**Tier:** SMALL (<100 LOC)  
**Head SHA (code):** `c82a6cf1`  
**LOC vs main:** +93 / −8  

## Experiment context

Part of a 3-tier Greptile vs standard code-reviewer comparison on an AFL-style Python fuzzer. GitHub Copilot was unavailable; **Cursor Bugbot** was used as the standard stand-in.

### Code changes in this tier
- Fix BLE CLI so bare `BLE` starts a fresh campaign (README-compatible)
- Pass absolute resume paths into BLE harness
- Add dictionary-token insert + splice mutations in `mutations.py`
- Bias havoc intensity for crash-hot HTTP endpoints in `simple_fuzzer2.py`

## Reviewer status

| Reviewer | Status | Notes |
|----------|--------|-------|
| **Greptile** (`greptile-apps[bot]`) | Received | Summary; confidence **5/5**; no inline P1/P2 |
| **GitHub Copilot** | **Not received** | Credits / collaborator 422 |
| **Cursor Bugbot** (stand-in) | Received | **No bugs** |

## What Greptile found

- Correctly characterized AFL-style mutation expansion and BLE command handling
- Related BLE entry-point changes to the downstream loader contract (path resolution)
- Confidence 5/5 — appears safe to merge; no false-positive defect spam
- No inline comments

## What Cursor Bugbot found

**No bugs.** Aligned with Greptile’s clean assessment.

Light human notes (not Bugbot): `strategy_hits` telemetry is recorded but never persisted/exported.

## What Copilot found

**Unavailable.** Cursor Bugbot substituted.

## Overlap

| Dimension | Result |
|-----------|--------|
| Defect findings | Both: none |
| False positives | Both: none |
| Unique Greptile | Merge confidence score + contract narrative |
| Unique Cursor | None material |

## Pitfalls and benefits (this tier)

### Greptile
- **Benefit:** Fast merge confidence without inventing defects  
- **Pitfall:** Little pedagogical comparison value when the PR is clean

### Cursor Bugbot
- **Benefit:** Same “clean” conclusion; free if Cursor is already licensed  
- **Pitfall:** No always-on GitHub PR check packaging in this experiment

## Verdict for small PRs
**Tie / low ROI for paid Greptile.** Either reviewer is enough for a clean <100 LOC change. Prefer Greptile only if you want always-on GitHub checks without opening Cursor.
