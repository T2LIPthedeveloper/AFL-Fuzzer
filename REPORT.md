# REPORT.md — PR #3 (Large tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3  
**Branch:** `develop-3` → `main`  
**Tier:** LARGE (~2432 / −23 vs `main`)  
**Code SHA:** `6a2233a35474118cac65ec89940e45996e2c93ec`  

> **Full experiment write-up (mechanisms, verbatim Greptile text, graph-hop analysis, buy checklist):**  
> [`GREPTILE_DIFFERENTIAL_CODE_REPORT.md`](./GREPTILE_DIFFERENTIAL_CODE_REPORT.md) · [`GREPTILE_DIFFERENTIAL_CODE_REPORT.html`](./GREPTILE_DIFFERENTIAL_CODE_REPORT.html)  
> **Naming:** In the collated report, **“Copilot” = Cursor Bugbot** (GitHub Copilot product unavailable).

## Code that existed vs what this PR adds
**Existed:** `simple_fuzzer2.py` HTTP greybox loop (`SeedQ`, energy, coverage probes, bug classifier), `mutations.py`, BLE harness, sessions.  
**Added:** `corpus_manager`, `coverage_bitmap`, `crash_triage`, `fuzz_stats`, `havoc_stage`, `seed_minimizer`, `session_replay` + wiring in `simple_fuzzer2.py` (includes small+medium tiers).

## Greptile (confidence 2/5)
Understood full pipeline; **3×P1**: `s_prime` telemetry hole; `bug_id` drop vs `FuzzStatsCollector`; minimizer `lambda: True`. Mermaid showed missing edges. TREX not observed.

## Copilot (Cursor Bugbot)
**2×high / 2×medium:** same telemetry + `bug_id` issues; plus corpus never selected by `choose_next_seed`; rarity-as-gain in `mark_result`. Missed minimizer predicate.

## Overlap / graph
Shared high-severity findings are **dataflow/call-graph** class. Greptile unique: minimizer policy. Copilot unique: corpus orphan + favoritism decay. See collated §7 / Appendix F.

## Verdict
Greptile earned its graph narrative on this PR; Copilot still caught most critical holes. Prefer Greptile for always-on GitHub packaging; don’t assume exclusive defect detection vs Cursor.
