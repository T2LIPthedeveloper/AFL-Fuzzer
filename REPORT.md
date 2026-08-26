# REPORT.md — PR #3 (Large tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3  
**Branch:** `develop-3` → `main`  
**Tier:** LARGE (1000+ LOC additive; ~2432 / −23 vs `main`)  
**Head SHA:** `6a2233a35474118cac65ec89940e45996e2c93ec`  

## Experiment context

Top rung of the Greptile vs GitHub Copilot (standard) comparison. Includes small + medium tiers **plus** a substantial greybox pipeline.

### Large-tier modules
- `corpus_manager.py` — weighted corpus, favoritism, persistence
- `coverage_bitmap.py` — edge-style coverage map for HTTP outcomes
- `crash_triage.py` — crash dedup / signature / optional minimize
- `fuzz_stats.py` — campaign counters + snapshots
- `havoc_stage.py` — stacked havoc mutations
- `seed_minimizer.py` — AFL-like trim for structured payloads
- `session_replay.py` — replay helpers + HTML campaign report
- Wiring in `simple_fuzzer2.py` (telemetry, havoc path, artifact persistence)

## Reviewer status

| Reviewer | Status | Notes |
|----------|--------|-------|
| **Greptile** | Received | Summary + **3 inline P1s**; confidence **2/5** |
| **GitHub Copilot** | **Not received** | Same access limitation as other PRs |

## What Greptile found

### Summary (confidence 2/5)
- Correctly identified the new corpus / coverage / triage / havoc / minimize / report pipeline
- Stated the PR is **not merge-safe** until telemetry plumbing and minimizer validation are fixed
- Listed files needing attention spanning `simple_fuzzer2.py` and multiple new modules (cross-file)

### Inline P1 findings (strong graph / dataflow character)

1. **Response telemetry loses outcomes (`simple_fuzzer2.py`)**  
   `update_energy_metrics` reads `status_code` / `response_body` / `error` from `s_prime`, but the request loop never copies local results into that dict.  
   **Effect:** coverage buckets collapse to generic `ERR`/`none`; crash signatures merge.  
   **Graph value:** dataflow between loop locals and metrics helper across the fuzzing pipeline.

2. **Crash identifiers dropped (`simple_fuzzer2.py` → `fuzz_stats.py`)**  
   Classifier bug IDs never reach `note_iteration(... bug_id=...)`, and `FuzzStatsCollector` only counts crashes when **both** `reveals_bug` and `bug_id` are set → reports show zero crashes.  
   **Graph value:** API contract between classifier, metrics update, and stats collector.

3. **Minimization discards coverage behavior (`simple_fuzzer2.py` + `seed_minimizer.py`)**  
   `lambda candidate: True` accepts every structural deletion; reduced seeds are stored as favored corpus entries without re-checking interestingness.  
   **Graph value:** predicate misuse across minimizer call site and corpus favoritism policy.

### Flowchart
Greptile produced a mermaid pipeline showing missing copy of result fields and missing `bug_id` forward edges — again highlighting **integration seams**, not typos.

## What Copilot found

**Pending / unavailable.** No Copilot review bot activity on PR #3.

### Placeholder for future Copilot capture
When Copilot runs, record:
- Local defect count (null checks, naming, unused imports)
- Whether it also flags telemetry plumbing / bug_id / trim predicate
- Whether findings are limited to single-hunk scope

## Overlap
- N/A until Copilot arrives  
- **Predicted:** Copilot may flag the obvious `lambda candidate: True` smell if it sees that hunk; less likely to prove the `bug_id` ∧ `reveals_bug` conjunction across `fuzz_stats.py` without whole-pipeline reading

## Pitfalls and benefits (this tier)

### Greptile — benefits
- Highest signal of the three PRs: multiple **true** integration defects
- Explicitly linked defects to undercounting in campaign reports (downstream impact)
- Confidence score aligned with severity

### Greptile — pitfalls
- Summary sometimes paraphrases filenames (`FuzzStatsCollector` vs local class naming variants)
- Dense HTML summary comments are harder to skim than inline annotations alone

### Copilot
- Still unknown; comparison incomplete without product enablement

## Verdict for large PRs
This is where Greptile’s graph/dataflow review is most valuable: the bugs are real, cross-module, and would ship silently (empty crash stats, polluted corpus). **Worth paying for** on large fuzzer/refactors *if* your alternative is line-local review only—pending Copilot confirmation once enabled.
