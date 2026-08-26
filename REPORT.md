# REPORT.md — PR #3 (Large tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3  
**Branch:** `develop-3` → `main`  
**Tier:** LARGE (1000+ LOC additive; ~2432 / −23 vs `main`)  
**Head SHA (code):** `6a2233a35474118cac65ec89940e45996e2c93ec`  

## Experiment context

Top rung of the Greptile vs standard code-reviewer comparison. Includes small + medium tiers **plus** a substantial greybox pipeline. GitHub Copilot code review was unavailable (credits / collaborator 422); **Cursor Bugbot** was used as the standard automated reviewer stand-in.

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
| **GitHub Copilot** | **Not received** | Credits / not a collaborator (422) |
| **Cursor Bugbot** (standard stand-in) | Received | 2 high + 2 medium on large-tier wiring |

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

## What Cursor Bugbot found (Copilot stand-in)

| Severity | Location | Finding |
|----------|----------|---------|
| high | `simple_fuzzer2.py:563-620` | Response metadata never attached to `s_prime` before coverage/triage/stats → collapsed buckets, default `"CRASH"`, empty status metrics |
| high | `simple_fuzzer2.py:625-634` | `note_iteration(reveals_bug=True)` omits `bug_id` → crash counters stay 0 despite triage/`FailureQ` |
| medium | `simple_fuzzer2.py:607-610` | `mark_result` uses `coverage_gain or coverage_score`; rarity term keeps corpus favored |
| medium | `simple_fuzzer2.py:1003-1115` | `CorpusManager` populated/persisted but `choose_next_seed` still only uses legacy `SeedQ` |

Inherited medium-tier issues (BLE unwired `record`/donor, schedule keying, missing `coverage_gain` arg) remain in the cumulative diff.

## What Copilot found

**Unavailable** (credits / collaborator access). Cursor Bugbot substituted as the comparable automated reviewer.

## Overlap (Greptile ∩ Cursor)

| Finding | Greptile | Cursor Bugbot |
|---------|----------|---------------|
| `s_prime` telemetry not plumbed | Yes (P1) | Yes (high) |
| `bug_id` dropped → zero crash stats | Yes (P1) | Yes (high) |
| Minimizer `lambda: True` | Yes (P1) | **No** (missed) |
| Corpus never selected for fuzzing | **No** | Yes (medium) |
| `mark_result` rarity-as-gain | **No** | Yes (medium) |
| Mermaid missing-edge diagrams | Yes | No |

**Overlap rate on shared high-severity defects:** 2/2 telemetry/crash-ID issues. Greptile uniquely caught the minimizer predicate; Cursor uniquely caught corpus dead-wiring and favoritism decay.

## Pitfalls and benefits (this tier)

### Greptile — benefits
- Highest signal of the three PRs: multiple **true** integration defects
- Explicitly linked defects to undercounting in campaign reports (downstream impact)
- Confidence score aligned with severity; flowchart aids explanation

### Greptile — pitfalls
- Missed corpus-vs-`SeedQ` selection disconnect (Cursor caught)
- Summary sometimes paraphrases filenames
- Dense HTML summaries harder to skim than inline-only tools

### Cursor Bugbot — benefits
- Matched Greptile on the two highest-impact dataflow bugs
- Found corpus unused for selection (classic “module added, queue not switched”)
- Found favoritism decay bug via score semantics

### Cursor Bugbot — pitfalls
- Missed `lambda: True` minimizer pollution (Greptile’s clearest policy bug)
- No confidence score / merge recommendation narrative
- No pipeline diagram

## Verdict for large PRs
Both reviewers delivered real integration findings. Greptile’s graph-style review still adds **incremental** value (minimizer predicate + impact narrative + diagrams), but Cursor was not “hunk-local only”—it also reasoned across call sites. **Paying for Greptile is strongest when you want merge confidence + cross-module policy bugs; Cursor alone already catches most critical telemetry holes on this PR.**
