# GREPTILE_DIFFERENTIAL_CODE_REPORT.md

**Document type:** End-to-end differential study of automated and human code review on AFL-Fuzzer  
**Repository:** [T2LIPthedeveloper/AFL-Fuzzer](https://github.com/T2LIPthedeveloper/AFL-Fuzzer)  
**Date:** 2026-08-26 (four-way comprehensive expansion)  
**Companion HTML:** `GREPTILE_DIFFERENTIAL_CODE_REPORT.html` (**full twin** of this document—not a summary)  
**Per-PR notes:** `REPORT.md` on `develop-1`, `develop-2`, `develop-3`

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Four reviewers defined](#2-four-reviewers-defined)
3. [Experiment methodology](#3-experiment-methodology)
4. [Baseline codebase that already existed](#4-baseline-codebase-that-already-existed)
5. [Code changes by tier (exhaustive inventory)](#5-code-changes-by-tier-exhaustive-inventory)
6. [How Greptile works](#6-how-greptile-works)
7. [How Copilot works](#7-how-copilot-works)
8. [How human-in-the-loop review works](#8-how-human-in-the-loop-review-works)
9. [What “no reviewer” implies](#9-what-no-reviewer-implies)
10. [Greptile tool use on these PRs](#10-greptile-tool-use-on-these-prs)
11. [Tier results — Small (PR #1)](#11-tier-results--small-pr-1)
12. [Tier results — Medium (PR #2)](#12-tier-results--medium-pr-2)
13. [Tier results — Large (PR #3)](#13-tier-results--large-pr-3)
14. [Master finding matrix (four-way)](#14-master-finding-matrix-four-way)
15. [Graph / AST necessity analysis](#15-graph--ast-necessity-analysis)
16. [Did Greptile understand the crux?](#16-did-greptile-understand-the-crux)
17. [Volume vs normal review](#17-volume-vs-normal-review)
18. [Pros and cons (four-way)](#18-pros-and-cons-four-way)
19. [Cost, latency, and process friction](#19-cost-latency-and-process-friction)
20. [Failure modes and pitfalls](#20-failure-modes-and-pitfalls)
21. [Scenario playbooks](#21-scenario-playbooks)
22. [Recommendation and buy decision](#22-recommendation-and-buy-decision)
23. [Appendices](#23-appendices)

---

## 1. Executive summary

This study compares **four review regimes** on the same three pull requests to `main`:

| Regime | Meaning in this document |
|--------|--------------------------|
| **No reviewer** | Merge/ship with zero code review—human or automated |
| **Copilot** | Automated “standard” AI review. **In this experiment:** Cursor Bugbot / Cursor agent review, because **GitHub Copilot code review could not run** (credits exhausted / collaborator API HTTP 422). Unless a sentence explicitly says “GitHub Copilot product,” **Copilot = Cursor Bugbot**. |
| **Greptile** | Greptile GitHub App (`greptile-apps[bot]`) with repository graph index + agentic PR review |
| **Human-in-the-loop alone** | A competent engineer reviewing without Greptile/Copilot bots—GitHub diff UI, local checkout, search (“find references”), judgment. Modeled from (a) what a careful senior would catch on these defects and (b) known human failure modes on integration bugs under time pressure |

### 1.1 PR ladder results at a glance

| Tier | Branch | PR | Code Δ vs `main` | No reviewer | Copilot | Greptile | Human alone (modeled) |
|------|--------|----|------------------|-------------|---------|----------|------------------------|
| Small | `develop-1` | [#1](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1) | +93 / −8 | Ships OK | 0 defects | 5/5, 0 defects | Would approve; maybe note unused `strategy_hits` |
| Medium | `develop-2` | [#2](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2) | +618 / −21 | **Ships broken schedulers** | 1H+4M+1L | 2/5, 2×P1 + outside-diff | Likely BLE unwired + donor; may miss keying/dict |
| Large | `develop-3` | [#3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3) | +2432 / −23 | **Ships lying telemetry/corpus** | 2H+2M (+ medium) | 2/5, 3×P1 | Likely telemetry/`bug_id`; variable on minimizer/corpus |

### 1.2 Headline conclusions

1. **No reviewer is unacceptable** for medium/large tiers: new modules look complete in the diff but are **partially unwired**. BLE energy never learns; HTTP schedule state conflates endpoints; coverage collapses; crash reports can show **zero** crashes; corpus artifacts diverge from live selection.
2. **Greptile understood the crux** at every tier and produced **integration / missing-edge** findings aligned with its graph + agentic-search marketing (confidence 5→2, Mermaid flowcharts of absent edges).
3. **Copilot matched Greptile on most critical defects** and found additional issues Greptile missed (`coverage_gain` omission, corpus unused, rarity-as-gain, dict parse).
4. **Human-in-the-loop alone** can catch the worst integration bugs *with time and diligence*, but is **inconsistent**, slower, and historically weak on call-graph orphans under diff fatigue. Humans uniquely add product/intent/ethics critique bots skip.
5. **TREX** (Greptile sandbox execution) **did not appear to run**—Greptile findings here are static reasoning, not runtime evidence.
6. **Best risk posture:** human-in-the-loop **plus** one automated reviewer (Greptile *or* Copilot)—not automation replacing humans, and not humans without automation on 2k+ LOC integration PRs.
7. **Pay for Greptile** when you need always-on GitHub packaging (confidence, diagrams, unattended P1s). **Do not expect a monopoly** on graph-class bugs versus Copilot/Cursor already reviewing thoroughly.

---

## 2. Four reviewers defined

### 2.1 No reviewer

- **Process:** Author merges after CI green (or without CI); no second read of the diff.
- **Information diet:** Author’s mental model only.
- **Strengths:** Zero latency, zero review cost, maximum velocity.
- **Weaknesses:** Integration bugs in *this* experiment are exactly what authors miss—they wrote the new module and assumed wiring. No adversarial “API exists but never called” pass.
- **Fit:** Trivial typos with tests. **Not** multi-file fuzzer pipeline grafts.

### 2.2 Copilot (Cursor Bugbot here; GitHub Copilot product documented)

**As used (Cursor Bugbot):**
- Invoked per branch with `Diff: branch changes` vs `main`.
- Emits severity-tagged findings with file/line.
- Does not auto-post to GitHub unless transcribed.
- On this repo: strong cross-file integration reasoning on medium/large.

**GitHub Copilot product (not run):**
- Assign as PR reviewer or enable auto-review; **Lite** vs **Balanced** effort.
- Agentic “full project context” via GitHub Actions; optional MCP/skills; cloud-agent fix PRs.
- Always leaves a **Comment** review (never Approve / Request changes)—does not satisfy required approvals.
- Consumes AI credits; some file types excluded (lockfiles, logs, SVG, …).

### 2.3 Greptile

- Builds a **repository graph** (files, functions, classes, imports, calls).
- v3 **agentic loop**: codebase search, learned rules, multi-hop exploration, optional git history.
- Posts PR summary, **confidence 0–5**, **P0/P1/P2** inline comments, optional Mermaid diagrams.
- Optional **TREX** runtime validation (not observed here).
- Learning via 👍/👎; custom `greptile.json` / `.greptile/` (not configured here).

### 2.4 Human-in-the-loop alone

- Reads GitHub “Files changed” and/or local `git diff main...HEAD`.
- Uses IDE “find references,” mentally simulates fuzz loops, maybe runs a smoke test.
- Asks: “Is this feature actually called?” and “What would the campaign report show after 100 iterations?”
- **Not modeled as perfect:** time pressure, fatigue on +2400 LOC, author bias, trust in modules that “look AFL-complete.”
- **Unique strengths:** threat modeling, product intent, whether AFL semantics are *correct* (not merely wired), BLE operational cost, dictionary ethics, merge strategy across stacked PRs.

### 2.5 Scoring axes used throughout

Detection likelihood · explanation quality · false-positive risk · latency · cost · consistency · merge-gate packaging · accountability.

---

## 3. Experiment methodology

### 3.1 Goals

1. Build three **additive** difficulty tiers of real AFL-fuzzer changes.
2. Open PRs to `main` so Greptile’s GitHub App reviews them.
3. Run Copilot-equivalent (Cursor) reviews on the same diffs.
4. Model **no reviewer** and **human-alone** outcomes against the same defect set.
5. Judge whether Greptile’s graph/AST/agentic story yields defects hard without structural context.
6. Produce buy/no-buy guidance with four-way nuance.

### 3.2 Branch ladder

```
main
  └── develop-1   (small)     ── PR #1 → main
        └── develop-2 (medium) ── PR #2 → main
              └── develop-3 (large) ── PR #3 → main
```

Higher PRs’ diffs to `main` **include** lower tiers.

### 3.3 SHAs under review (code, pre-report commits)

| Tier | Code SHA |
|------|----------|
| Small | `c82a6cf196bb3d1bfe4434088ce1092784db85d8` |
| Medium | `ce356ed1471c78092f0c05769c7c780d064b0163` |
| Large | `6a2233a35474118cac65ec89940e45996e2c93ec` |

### 3.4 Evidence sources

- Greptile issue + inline comments on PRs #1–#3 (captured 2026-08-26).
- Cursor Bugbot findings for each `develop-*` vs `main`.
- Greptile docs/blog: introduction, graph-based codebase context, anatomy of a review, key features / TREX, v3 agentic rewrite, TREX execution blog.
- GitHub Copilot code review documentation (concepts + how-to).
- Local inspection of `fuzz_stats.note_iteration`, `choose_next_seed`, BLE `afl_fuzz` loop, etc.

### 3.5 What this study is not

- Not a statistically powered A/B across hundreds of PRs.
- Not a TREX evaluation.
- Not a live GitHub Copilot Balanced head-to-head (blocked).
- Not a claim that Cursor ≡ GitHub Copilot product quality.
- Human column is **modeled**, not a separate double-blind hired review.

---

## 4. Baseline codebase that already existed

On `main` before the experiment, AFL-Fuzzer already contained a multi-target fuzzing workspace.

### 4.1 HTTP / Django greybox path

- **`simple_fuzzer2.py` (`FuzzerClient`):** OpenAPI-driven seed queue (`SeedQ`), mutation intensity, energy heuristics, coverage probes, crash correlation, bug classification, session folders, `choose_next_seed` cycling path/method pairs.
- **`mutations.py` (`MutationEngine`):** bitflip, interesting integers, special chars, structured payload walking, `random_mutation`, `mutate_payload`.
- Supporting classifiers, session persistence, coverage helpers as previously merged.

### 4.2 BLE path

- **`BLE/Smartlock.py`:** async AFL-like loop—queue, `mutate_input`, `assign_energy`, `choose_next`, interestingness, reconnect cadence, resume JSON.
- **`BLEClient`:** connect / write / log helpers.
- Launcher wiring through **`main.py`** interactive commands.

### 4.3 Why the baseline matters

Medium/large changes **deliberately grafted** new schedulers / corpus / telemetry onto these loops. Review value is almost entirely about whether reviewers notice **incomplete grafts**—not whether new files parse as Python.

---

## 5. Code changes by tier (exhaustive inventory)

### 5.1 Small — `develop-1` — +93 / −8 across 3 files

| File | Approx Δ | What changed | Intent |
|------|----------|--------------|--------|
| `main.py` | +11 / −5 | Bare `BLE` early-return; resume path resolved to absolute | CLI matches README / `run.sh`; resume loads reliably |
| `mutations.py` | +70 / −2 | `dictionary_tokens`, `dictionary_insert`, `splice`, `_record_strategy`; strategies extended | AFL-like dictionary + splice diversity |
| `simple_fuzzer2.py` | +15 / −3 | Crash-hot havoc bias; ~15% same-path splice | More mutation stack near crashy endpoints |

**Crux:** Refine mutations + BLE ergonomics; no architecture rewrite.  
**Risk if unreviewed:** Low. Worst case: mutation mix shifts; resume mismatch is *fixed* by the PR.

### 5.2 Medium — unique `develop-1`→`develop-2` — +525 / −13 across 6 files

| File | Δ | What changed | Intent |
|------|---|--------------|--------|
| `power_schedule.py` | +249 (new) | Modes explore/exploit/COE/fast/linear/quad; `SeedStats`; `calculate_energy`; summary | AFL-like HTTP energy |
| `ble_energy.py` | +144 (new) | `BLEEnergyScheduler`, transitions, `record`, `energy_for`, `rank_queue`, `splice_sequences` | BLE novelty/crash-aware energy |
| `dictionaries/http_api.dict` | +42 (new) | HTTP/API tokens | Richer dictionary mutations |
| `mutations.py` | +22 | `from_dictionary_file` AFL dict parser | Load tokens from file |
| `simple_fuzzer2.py` | +43 / −~8 | Dict engine; `PowerSchedule`; energy blend; persist snapshot; `record_execution` | Connect schedule to HTTP fuzzer |
| `BLE/Smartlock.py` | +38 / −~7 | Scheduler import; interesting-byte; donor-capable mutate; energy/choose via scheduler | Connect schedule to BLE fuzzer |

**Crux:** Add scheduling subsystems. **Latent bug class:** read paths wired; write/donor paths not.  
**Risk if unreviewed:** High—feature appears shipped; BLE energy never learns; identical HTTP bodies share energy across endpoints.

### 5.3 Large — unique `develop-2`→`develop-3` — +1821 / −9 across 8 files

| File | Δ | What changed | Intent |
|------|---|--------------|--------|
| `corpus_manager.py` | +316 (new) | Weighted corpus, favoritism, persistence, selection APIs | AFL-like queue |
| `coverage_bitmap.py` | +252 (new) | Outcome edges, interesting scores | Lightweight coverage |
| `crash_triage.py` | +292 (new) | Signatures, dedup, optional minimize | Crash hygiene |
| `fuzz_stats.py` | +208 (new) | Counters; crashes counted iff `reveals_bug and bug_id` | Campaign metrics |
| `havoc_stage.py` | +202 (new) | Stacked havoc | Mutation depth |
| `seed_minimizer.py` | +198 (new) | Structural trim with interestingness predicate | Seed minimization |
| `session_replay.py` | +217 (new) | Replay helpers + HTML report | Artifacts |
| `simple_fuzzer2.py` | +145 / −~9 | Wire all of the above into metrics / sessions / mutations | Integration |

**Crux:** Full greybox pipeline. **Latent bug class:** telemetry plumbing, API contracts, corpus not selected, dishonest minimizer predicate.  
**Risk if unreviewed:** Very high—dashboards lie; favored corpus polluted; new corpus unused for live selection.

### 5.4 Cumulative LOC vs `main`

| Branch tip (code) | Insertions | Deletions |
|-------------------|------------|-----------|
| `develop-1` | 93 | 8 |
| `develop-2` | 618 | 21 |
| `develop-3` | 2432 | 23 |

---

## 6. How Greptile works

### 6.1 Indexing / graph construction

When a repository is connected, Greptile builds a **complete graph** of code elements:

1. **Parse** files → extract directories, files, functions, classes, variables (AST-level structure).
2. **Map relationships** → function calls, imports, dependencies, variable usage.
3. **Store** the graph for query during reviews.

Secondary writeups of Greptile-style semantic graphs also mention natural-language summaries per unit, **embeddings** in a vector store, and edges for call/import **and** embedding similarity. Core product claim: reviews reason about **ripple effects beyond the diff**.

### 6.2 v3 agentic detective loop

Greptile v3 replaced a rigid flowchart (diff → fixed context → comments) with a loop that can repeatedly:

- search the codebase,
- follow nested calls,
- compare similar implementations,
- optionally consult git history,
- apply learned rules,

with high tool/inference budgets. Vendor-published v3 metrics include large gains in upvote ratio and action rate versus v2, attributed partly to a higher “sureness” threshold (fewer low-confidence nits).

### 6.3 Anatomy of a Greptile PR review

- Analyzing (👀, often ~3 minutes) → Complete (👍)
- **Summary:** what the PR does + issues found
- **Confidence 0–5:** merge readiness (5 = production ready; 2 = significant bugs / needs rework)
- **Inline comments** with **P0 / P1 / P2** severity badges
- **Diagrams:** sequence / ER / class / **flow** (flow diagrams appeared on our medium and large PRs)
- Suggested fixes; “Fix with your Agent”; learning via reactions

### 6.4 Optional capabilities

Custom rules, cross-repo clusters, MCP IDE tools, analytics, **TREX** (write/run tests in an isolated sandbox; attach logs/screenshots/traces). Public billing messaging centers on seats + credits (TREX reviews consume more credits than standard reviews)—confirm current pricing in-product.

---

## 7. How Copilot works

### 7.1 GitHub Copilot code review (product)

- Reviews any language; often suggests one-click fixes.
- Trigger: reviewers sidebar, auto-review policies, or CLI.
- **Lite** vs **Balanced** effort (Balanced routes to higher-reasoning analysis; more AI credits).
- Agentic capabilities: full project context gathering (Actions runners); pass suggestions to Copilot cloud agent; MCP servers / agent skills when configured.
- Always a **Comment** review—does not block merges via required approvals.
- Cost: AI credits + Actions minutes for agentic features; some files excluded.

### 7.2 Copilot in this experiment (Cursor Bugbot)

- Local/branch diff review with severity findings.
- No confidence score, no Mermaid, no automatic GitHub inline threads unless pasted.
- Here: behaved as a **strong static integration reviewer**, not a style-nit bot.

### 7.3 Implications for the four-way comparison

The Copilot column is the **best available automated “standard” reviewer we could actually run**. External validity to GitHub Copilot Balanced should be re-checked when credits return.

---

## 8. How human-in-the-loop review works

### 8.1 Ideal human process on these PRs

1. Read PR description / commits for intent (scheduling, corpus, telemetry).
2. Skim new modules for API surface (`record`, `note_iteration`, `trim`, choose/select).
3. **Find references** from campaign loops to those APIs.
4. Trace one HTTP iteration and one BLE iteration end-to-end on paper.
5. Ask what `power_schedule.json` / HTML campaign report would show after 100 iterations.
6. Optionally run a short fuzz smoke or unit-instantiate new classes.
7. Leave blocking comments on unwired edges; approve only after fixes or explicit follow-ups.

### 8.2 Realistic human failure modes (applied here)

- **Diff fatigue** on +2400 LOC: deep-read new files; skim wiring in `simple_fuzzer2.py`.
- **Completeness illusion:** `ble_energy.py` looks finished → skip call-site audit.
- **Author bias** if the same person wrote and reviewed.
- **Time boxing:** catch two of five issues; ship the rest.
- **Under-weighting** “reports show zero crashes” without running a campaign.

### 8.3 What humans uniquely catch (bots weak)

- Whether dictionary tokens are appropriate for the target (ethics / scope).
- Whether BLE reconnect/sleep constants remain sane under higher energy.
- Whether three stacked PRs to `main` is the right merge strategy.
- Whether HTTP status/body hashing is scientifically meaningful “coverage” versus marketing language.

---

## 9. What “no reviewer” implies

Counterfactual: each PR merges as authored.

| Tier | Likely production outcome without review |
|------|------------------------------------------|
| Small | Mostly fine; richer mutations; BLE resume fixed |
| Medium | BLE scheduler never learns; splice dead; HTTP energy conflates identical bodies across endpoints; engineers may “tune” schedules that are not learning |
| Large | Coverage buckets collapse; crash HTML/stats show **0**; minimized junk favored; on-disk corpus diverges from live `SeedQ` selection |

**Additional risk:** dictionary tokens include XSS/SQLi-like strings—expected for a fuzzer, dangerous if aimed at production without isolation. No reviewer also means no confirmation of target-environment assumptions.

---

## 10. Greptile tool use on these PRs

| Capability | Observed? | Evidence |
|------------|-----------|----------|
| Graph / index queries | **Strongly indicated** | Cross-file contracts; files-needing-attention lists; missing-edge diagrams |
| Agentic codebase search | **Strongly indicated** | Outside-diff donor call; `FuzzStatsCollector` conjunction defined in another new file |
| Learned rules / memory | Not evidenced | Fresh experiment; no training window |
| Custom `greptile.json` | No | Not present in repo |
| Cross-repo clusters | N/A | Single repository |
| TREX sandbox | **No** | No logs, screenshots, or generated tests attached to comments |
| Fix-with-Agent UX | Product feature | Not evaluated as a remediation workflow |

**Conclusion:** Greptile used **static graph/search reasoning + diagram generation**. It did **not** demonstrate runtime proof via TREX on these PRs.

---

## 11. Tier results — Small (PR #1)

### 11.1 Greptile

- Confidence **5/5**.
- Accurate summary: bare `BLE`, absolute resume paths, dictionary insert, splice, strategy telemetry, crash-associated intensity.
- Inline defects: none.
- Noted BLE entry-point changes match the downstream loader contract.

### 11.2 Copilot

- **0 bugs.**

### 11.3 Human-in-the-loop alone (modeled)

- **Likely:** approve after confirming absolute resume path reaches `start_ble_fuzzing` / existence checks.
- **Maybe:** note `strategy_hits` never persisted/exported.
- **Unlikely:** invent false blockers.

### 11.4 No reviewer

- Ships an acceptable small improvement.

### 11.5 Four-way verdict (small)

| Regime | Outcome quality | Value add |
|--------|-----------------|-----------|
| No reviewer | Acceptable | Velocity |
| Copilot | Acceptable (clean bill) | Confirmation |
| Greptile | Acceptable + confidence 5/5 | Stakeholder packaging |
| Human alone | Acceptable | Intent check |

**ROI of paid automation on small clean PRs: low.**

---

## 12. Tier results — Medium (PR #2)

### 12.1 Greptile (confidence 2/5)

- **P1:** BLE scheduler scores stay empty (`record` never called).
- **P1:** Endpoint statistics conflated (payload-only fingerprint).
- **Outside-diff:** BLE splicing unreachable (no donor argument).
- **Mermaid:** missing `record` edge + donor-not-supplied edge.

### 12.2 Copilot

| Severity | Finding |
|----------|---------|
| high | `ble_scheduler.record()` never called |
| medium | donor splice never invoked |
| medium | payload-only schedule keys |
| medium | `coverage_gain` always defaults to 0 at call site |
| low | dictionary loader corrupts tokens containing `=` and `"` |

Soft/disputed: claim that dictionary tokens never reach `mutate_payload`—`mutate_payload` → `random_mutation` can still select `dictionary_insert`.

### 12.3 Human-in-the-loop alone (modeled)

- **High:** notice `mutate_input(seed)` vs new donor parameter if carefully reviewing `Smartlock.py`.
- **High:** ask “who calls `record`?” when reading `ble_energy.py`.
- **Medium:** catch payload-only fingerprint (requires multi-endpoint mental model).
- **Lower:** catch dict `=`/`"` parse without adversarial examples.
- **Medium:** miss `coverage_gain` omission (defaults hide bugs).

### 12.4 No reviewer

- Merges **broken BLE learning** and **cross-endpoint schedule bleed**.

### 12.5 Four-way verdict (medium)

Automation (Greptile **or** Copilot) substantially beats no reviewer. Human alone can match if diligent. Greptile wins packaging; Copilot slightly broader issue list.

---

## 13. Tier results — Large (PR #3)

### 13.1 Greptile (confidence 2/5)

- **P1:** Response telemetry loses outcomes (`s_prime` fields unset).
- **P1:** Crash identifiers dropped (`bug_id` / `FuzzStatsCollector` conjunction).
- **P1:** Minimization discards coverage behavior (`lambda candidate: True`).
- **Mermaid:** result fields not copied; `bug_id` not forwarded; minimizer → favored corpus.
- **Files needing attention:** `simple_fuzzer2.py`, `fuzz_stats.py`, `coverage_bitmap.py`, `crash_triage.py`, `seed_minimizer.py`, `corpus_manager.py`.

### 13.2 Copilot

| Severity | Finding |
|----------|---------|
| high | response metadata never attached to `s_prime` before coverage/triage/stats |
| high | `bug_id` omitted → crash stats stay 0 |
| medium | `mark_result` treats rarity / interesting_score as coverage gain |
| medium | `CorpusManager` populated/persisted but `choose_next_seed` still uses only `SeedQ` |

### 13.3 Human-in-the-loop alone (modeled)

- **High:** “where do status_code/body get onto `s_prime`?” if tracing one request.
- **High/medium:** `bug_id` plumbing if they open `fuzz_stats.py`.
- **Medium:** spot `lambda: True` as a smell; may rationalize as “structural only.”
- **Medium/low under fatigue:** notice corpus never selected (long `choose_next_seed` after seven new modules).
- **Unique human:** challenge whether HTTP status/body bitmap is valid research “coverage.”

### 13.4 No reviewer

- Merges **lying dashboards**, **polluted favored corpus**, and a **dead corpus manager** relative to live selection—the worst blind-merge tier.

### 13.5 Four-way verdict (large)

No reviewer fails hard. Greptile ∪ Copilot covers nearly the full defect set. Human alone can catch critical telemetry but is least consistent on orphans under fatigue. Ideal: **human + (Greptile or Copilot)**.

---

## 14. Master finding matrix (four-way)

Legend: ✓ detected · ~ partial/possible · ✗ not detected · n/a · **H** = modeled human likelihood

| Finding | Tier | Graph-ish? | No rev | Copilot | Greptile | Human alone |
|---------|------|------------|--------|---------|----------|-------------|
| Clean small / no false bugs | S | No | n/a | ✓ | ✓ | ✓ |
| Unused `strategy_hits` export | S | No | ✗ | ✗ | ✗ | ~ |
| BLE `record` never called | M | **Yes** | ✗ | ✓ | ✓ | **H high** |
| BLE donor splice dead | M | **Yes** | ✗ | ✓ | ✓ | **H high** |
| Schedule payload-only key | M | Partial | ✗ | ✓ | ✓ | **H med** |
| `coverage_gain` always 0 | M | **Yes** | ✗ | ✓ | ✗ | **H med-low** |
| Dict `=`/`"` parse bug | M | No | ✗ | ✓ | ✗ | **H low** |
| `s_prime` telemetry hole | L | **Yes** | ✗ | ✓ | ✓ | **H high** |
| `bug_id` drop / stats ∧ | L | **Yes** | ✗ | ✓ | ✓ | **H high-med** |
| Minimizer `lambda: True` | L | Partial | ✗ | ✗ | ✓ | **H med** |
| Corpus never selected | L | **Yes** | ✗ | ✓ | ✗ | **H med-low** |
| Rarity-as-gain favoritism | L | Partial | ✗ | ✓ | ✗ | **H low-med** |
| Confidence score / merge UX | — | Product | ✗ | ✗ | ✓ | ~ (written approval) |
| Missing-edge Mermaid | — | Product | ✗ | ✗ | ✓ | ~ (whiteboard) |
| Runtime proof (TREX/tests) | — | Exec | ✗ | ✗ | ✗ | ~ if human runs smoke |
| Product/ethics/methodology critique | — | Human | ✗ | ✗ | ✗ | ✓ **unique** |

### 14.1 Defect detection counts (medium+large substantive defects)

Counting ~10 substantive defects (excluding clean-PR row, pure UX rows, ethics):

| Regime | Detected | Missed | Notes |
|--------|----------|--------|-------|
| No reviewer | 0 | 10 | By definition |
| Copilot | 8 | 2 | Missed minimizer; soft miss on `strategy_hits` |
| Greptile | 6 | 4 | Missed coverage_gain, dict parse, corpus unused, rarity-as-gain |
| Human alone | ~5–8 | ~2–5 | High variance; diligent mid ~6–7 |

**Union(Copilot, Greptile) ≈ 9/10 substantive.**  
**Union(Human, either bot)** approaches full coverage including ethics/methodology.

---

## 15. Graph / AST necessity analysis

### 15.1 Strongly requires multi-hop / call-graph / dataflow

1. BLE `record` missing while readers exist.
2. Donor never supplied.
3. `s_prime` field plumbing across loop → metrics → coverage/triage.
4. `bug_id` contract across classifier → metrics → `fuzz_stats`.
5. Corpus module vs `choose_next_seed` still on `SeedQ`.

### 15.2 Locally visible; impact needs graph/policy context

1. Payload-only fingerprint.
2. `lambda: True` + favored corpus.
3. Rarity term used as coverage gain.

### 15.3 Local / lexical

1. Dictionary parser `=`/`"` heuristic.

### 15.4 Critical nuance

**Graph reasoning mattered; Greptile’s hosted graph was not the only way to get it.** Copilot (Cursor) performed several multi-hop detections without Greptile’s index. Humans with “Find References” do the same more slowly. Greptile’s differentiator is **forcing that reasoning unattended on every PR** plus packaging (confidence, diagrams).

---

## 16. Did Greptile understand the crux?

| Tier | Crux | Greptile understanding | Grade |
|------|------|------------------------|-------|
| Small | Mutation refinements + BLE CLI | Exact | A |
| Medium | Schedulers must *learn* via feedback | Explicitly called out unreachable feedback/splice | A |
| Large | Pipeline must plumb results/IDs; honest minimize | Explicit telemetry / `bug_id` / predicate failures | A |

Greptile did **not** fully inventory every orphan (corpus selection). Intent understanding was excellent; defect-search completeness was very good but not perfect.

---

## 17. Volume vs normal review

| Expectation | No rev | Copilot | Greptile | Human |
|-------------|--------|---------|----------|-------|
| Style nit flood | — | No | No | Sometimes |
| Restate PR only | — | No—issues filed | No—issues filed | Varies |
| Comment count | 0 | Medium, broader | Low, high severity | Variable |
| False positives | — | One soft FP | Very low here | Possible bikesheds |
| vs noisy linter bot | — | Fewer, better | Fewer, better | N/A |

Greptile delivered **more severity-weighted value than a normal linter bot**, not more raw comments than Copilot.

---

## 18. Pros and cons (four-way)

### 18.1 No reviewer

**Pros:** Instant merge; zero seat cost; no review thrash.  
**Cons:** Blind to integration orphans; lying metrics on large tier; no institutional memory; unacceptable for this defect class.

### 18.2 Copilot

**Pros:** Strong defect recall here; catches extras Greptile missed; fits IDE workflow; GitHub product offers Balanced/MCP path.  
**Cons:** Credits/access blocked the product; Cursor path not always-on GitHub; no confidence/diagram packaging; missed minimizer; soft FP risk; Comment-only reviews do not gate merges.

### 18.3 Greptile

**Pros:** Always-on; confidence scores; Mermaid; P-levels; true integration P1s; crux-aware summaries; optional TREX/rules/learning.  
**Cons:** Paid; missed several real issues; TREX unused here; paraphrased names; dense HTML summaries; overlap with Copilot reduces uniqueness-for-price.

### 18.4 Human-in-the-loop alone

**Pros:** Intent/ethics/methodology; can run smokes; accountable decisions; best at “should we build this.”  
**Cons:** Slow; inconsistent; fatigues on large diffs; expensive senior time; may miss exact orphans bots found; not 24/7.

---

## 19. Cost, latency, and process friction

| Regime | Latency | Direct $ | Friction |
|--------|---------|----------|----------|
| No reviewer | Minutes | $0 | Deferred incident/debug cost |
| Copilot (Cursor) | Minutes–tens of minutes (manual) | Cursor subscription (often sunk) | Must remember to run |
| Copilot (GitHub product) | Seconds–minutes | AI credits / plan | Org policy enablement |
| Greptile | ~3 minutes typical | Seats + credits (+ TREX) | App install; tune nitpickiness |
| Human alone | Hours for large PR | Salary / opportunity cost | Scheduling; context switch |

Greptile’s sticker price may be cheaper than a week debugging silent crash stats—yet **redundant** if Cursor/GitHub Copilot reviews are already mandatory and effective.

---

## 20. Failure modes and pitfalls

### 20.1 Shared automation pitfalls

- Hallucinated APIs (not seen here).
- Over-confidence without runtime (no TREX / no human smoke).
- Missing product-level wrongness (what “coverage” means).

### 20.2 Greptile-specific pitfalls

- Outside-diff comments easy to miss in the GitHub UI.
- Assuming graph ⇒ unique findings (false vs Copilot in this study).
- Paying for TREX but leaving it disabled.

### 20.3 Copilot-specific pitfalls

- Credit exhaustion → silent absence (this experiment).
- Comment-only reviews do not block merge.
- Lite effort may under-analyze 2k LOC PRs (untested here).

### 20.4 Human-specific pitfalls

- Diff fatigue; author bias; “looks AFL-complete” illusion; time boxing; inconsistent depth.

### 20.5 No-reviewer pitfalls

- Exactly the medium/large outcomes in §9.

---

## 21. Scenario playbooks

### 21.1 Solo researcher, Cursor already paid

Prefer **human + Copilot (Cursor)**. Add Greptile only if you want unattended GitHub comments for collaborators or future-you.

### 21.2 Team with required PR reviews on GitHub

Prefer **human + Greptile** (or human + GitHub Copilot Balanced). Greptile’s confidence/diagrams help non-authors triage.

### 21.3 Compliance / audit narrative needed

Greptile’s persisted PR summaries + severity badges create an audit trail. Pair with human sign-off. No-reviewer fails audits; Copilot-only may lack merge packaging depending on setup.

### 21.4 Maximum defect recall on a scary PR

Run **Greptile and Copilot**, then human triage of the union. This study’s union caught nearly all substantive issues.

### 21.5 Budget cut

Cut Greptile before cutting human review. Cutting human and keeping only a bot is worse than the reverse for accountability—but cutting *both* automation and human on large integration PRs is worst.

---

## 22. Recommendation and buy decision

### 22.1 Ranked postures (best → worst) for this codebase

1. **Human-in-the-loop + Greptile** (or + Copilot): best defect union + accountability + packaging  
2. **Human + Copilot** if Greptile budget is tight and Cursor/GitHub Copilot is already paid  
3. **Greptile alone** or **Copilot alone**: far better than nothing; expect residual misses  
4. **Human alone**: acceptable with senior diligence; fragile under load / fatigue  
5. **No reviewer**: unacceptable for medium/large tiers

### 22.2 Should you pay for Greptile?

| Question | Answer |
|----------|--------|
| vs no reviewer | **Yes** |
| vs human alone | **Yes as a supplement**, not a replacement |
| vs Copilot already mandatory | **Situational** — buy for unattended GitHub UX / diagrams / confidence; marginal unique defect rate |
| Enable TREX if paying? | **Yes**—otherwise leaving a major differentiator off |
| Shop is mostly tiny clean PRs | Weak ROI |

### 22.3 Concrete next steps

1. Fix the union of P1/high findings on `develop-3` before merging any tier to `main`.  
2. Re-run **GitHub Copilot Balanced** when credits return; append a true product column.  
3. Enable **TREX** on a replay of PR #3; compare runtime evidence vs static comments.  
4. Keep **human approval required** on `main`.

---

## 23. Appendices

### Appendix A — Verbatim Greptile summaries (essence)

**PR #1:** Expands AFL-style mutation behavior and adjusts BLE command handling; bare `BLE`; resolved resume paths; dictionary insertion; splicing; strategy telemetry; crash-associated intensity. Confidence **5/5**.

**PR #2:** Adds AFL-inspired HTTP/BLE scheduling, dictionary mutations, splicing, resume handling; BLE feedback scheduling and splicing unreachable; HTTP scheduling conflates identical payloads across endpoints. Confidence **2/5**. Files needing attention: `BLE/Smartlock.py`, `power_schedule.py`.

**PR #2 P1 (empty scores):** `assign_energy` / `choose_next` read scheduler without `ble_scheduler.record` → length-only energy.

**PR #2 P1 (conflated stats):** `ensure_stats` keys only on payload fingerprint → cross-endpoint bleed.

**PR #2 outside-diff:** `mutate_input(seed)` omits donor → splice unreachable.

**PR #3:** Adds corpus / coverage / scheduling / crash-triage / havoc / minimize / replay / report; loses request-result data and bug IDs before telemetry; unverified minimized payloads favored. Confidence **2/5**.

**PR #3 P1 (telemetry):** loop never copies status/body/error into `s_prime` → collapsed coverage / merged crashes.

**PR #3 P1 (`bug_id`):** `note_iteration` without `bug_id` while collector requires `reveals_bug and bug_id` → zero crashes in reports.

**PR #3 P1 (minimizer):** `lambda candidate: True` accepts every deletion; favored corpus polluted.

### Appendix B — Graph-hop reconstructions

- **BLE `record`:** define scheduler → wire readers in `Smartlock.py` → search writers → zero `record` calls → length-only energy.  
- **Donor:** new parameter → only call site omits donor → dead branch.  
- **`s_prime`:** metrics read fields → loop never sets them → coverage/triage degrade.  
- **`bug_id`:** classifier id → not passed → `fuzz_stats` conjunction → zero counts.  
- **Minimizer:** `True` predicate → trim always succeeds → favored add → policy bug.  
- **Corpus unused:** corpus `add`/`save` → `choose_next_seed` only uses `SeedQ` → architectural orphan.

### Appendix C — Confidence and counts

| PR | Greptile conf | Greptile P1 | Outside | Copilot H | Copilot M | Copilot L |
|----|---------------|-------------|---------|-----------|-----------|-----------|
| #1 | 5/5 | 0 | 0 | 0 | 0 | 0 |
| #2 | 2/5 | 2 | 1 | 1 | 4 | 1 |
| #3 | 2/5 | 3 | 0 | 2 | 2 | 0 |

### Appendix D — References

1. https://www.greptile.com/docs/introduction  
2. https://www.greptile.com/docs/how-greptile-works/graph-based-codebase-context  
3. https://www.greptile.com/docs/code-review/first-pr-review  
4. https://www.greptile.com/docs/code-review/key-features  
5. https://www.greptile.com/blog/greptile-v3-agentic-code-review  
6. https://www.greptile.com/blog/trex-code-execution  
7. https://docs.github.com/en/copilot/concepts/agents/code-review  
8. https://docs.github.com/copilot/using-github-copilot/code-review/using-copilot-code-review  
9. https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1 · [/pull/2](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2) · [/pull/3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3)

### Appendix E — Status stamp

- Greptile: complete on PRs #1–#3  
- GitHub Copilot product: unavailable  
- Copilot (Cursor Bugbot): complete  
- Human-in-the-loop: modeled (not a separate hired blind review)  
- No reviewer: counterfactual  
- TREX: not observed  
- Document revision: four-way comprehensive expansion with full HTML twin  

### Appendix F — Glossary

- **AST:** Abstract Syntax Tree—structural parse of code.  
- **Call graph:** nodes = functions; edges = calls.  
- **Dataflow:** how values move across variables and calls.  
- **HITL:** Human-in-the-loop.  
- **P0/P1/P2:** Greptile severity badges.  
- **TREX:** Greptile Test / Run / Execute sandbox agent.  
- **SeedQ:** legacy HTTP seed queue inside `FuzzerClient`.  
