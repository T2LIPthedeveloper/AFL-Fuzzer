# GREPTILE_DIFFERENTIAL_CODE_REPORT.md

## Executive summary

This document is an end-to-end comparison of **Greptile** (graph-/agentic AI PR review) versus **Copilot** (in this experiment: **Cursor Bugbot / Cursor agent code review**, used as the stand-in because GitHub Copilot code review could not run—credits exhausted / collaborator API 422). Throughout this report, **“Copilot” means that Cursor-based review**, unless a sentence explicitly says “GitHub Copilot product.”

Three additive PRs were opened against `main`:

| Tier | Branch | PR | Code Δ vs `main` | Greptile | Copilot (Cursor) |
|------|--------|----|------------------|----------|------------------|
| Small | `develop-1` | [#1](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1) | +93 / −8 | Confidence **5/5**, 0 inline | **0 bugs** |
| Medium | `develop-2` | [#2](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2) | +618 / −21 | Confidence **2/5**, 2×P1 + 1 outside-diff | 1 high, 4 medium, 1 low |
| Large | `develop-3` | [#3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3) | +2432 / −23 | Confidence **2/5**, 3×P1 | 2 high, 2 medium (+ inherits medium issues) |

**Headline conclusion:** Greptile **understood the crux** of each PR (AFL-style mutation → scheduling → full greybox pipeline) and produced **integration / missing-edge** findings that align with what its marketing claims graph + agentic search are for. Copilot (Cursor) **matched Greptile on most critical defects** and found additional wiring/semantic issues Greptile missed. Greptile uniquely caught the minimizer `lambda: True` policy bug and packaged reviews with confidence scores + Mermaid flowcharts. **TREX (sandbox execution) does not appear to have run** on these PRs—findings are static reasoning, not runtime evidence. Paying for Greptile is **justified for always-on GitHub review UX and diagram/confidence packaging**; vs Cursor alone it is **incremental, not magical**—many “graph-looking” bugs were also found by Copilot without Greptile’s hosted index.

Per-PR companion writeups: `REPORT.md` on each `develop-*` branch.

---

## 1. Experiment methodology

### 1.1 Goals
1. Create three **additive** difficulty tiers of real fuzzer changes.
2. Open PRs to `main` so Greptile’s GitHub App reviews them.
3. Compare against a **standard** automated reviewer (intended: GitHub Copilot; actual: Cursor Bugbot labeled “Copilot” here).
4. Judge whether Greptile’s **graph / AST / agentic search** story yields defects that are hard without structural codebase context.
5. Produce this collated analysis for a buy/no-buy decision.

### 1.2 Branch ladder
```
main
  └── develop-1   (small)     ── PR #1 → main
        └── develop-2 (medium) ── PR #2 → main
              └── develop-3 (large) ── PR #3 → main
```
Each higher PR’s diff to `main` **includes** lower tiers.

### 1.3 What existed before (baseline on `main`)
The repository already contained a working multi-target fuzzer stack, including approximately:
- `simple_fuzzer2.py` — Django/OpenAPI greybox HTTP fuzzer (`FuzzerClient`, `SeedQ`, energy heuristics, coverage probes, bug classification, session folders).
- `mutations.py` — `MutationEngine` (bitflip, arithmetic, special chars, payload walkers).
- `main.py` — interactive project launcher (Django / BLE / …).
- `BLE/Smartlock.py` + `BLEClient` — BLE smart-lock AFL-style loop (queue, mutate, interestingness, energy).
- Supporting pieces: dictionaries folder patterns, sessions, bug classifiers, etc.

**Important:** Medium/large tiers deliberately added **new modules** and **partially wired** them into existing loops—the classic “looks complete in the diff hunk, broken in the call graph” failure mode that graph reviewers advertise.

### 1.4 Reviewers actually used

| Name in this report | Actual system | How it was invoked |
|---------------------|---------------|--------------------|
| **Greptile** | Greptile GitHub App (`greptile-apps[bot]`) | Automatic on PR open; summaries + inline P1s captured from PR comments |
| **Copilot** | **Cursor Bugbot** (Cursor review subagent) on each branch vs `main` | Manual: checkout branch → Bugbot `Diff: branch changes` / `Base Branch: main` |
| GitHub Copilot (product) | Not available | Credits / `requested_reviewers` 422; `@copilot` produced no reviews |

### 1.5 Evidence sources
- Greptile PR summary comments and inline review comments on PRs #1–#3 (captured 2026-08-26).
- Cursor Bugbot finding objects for develop-1/2/3.
- Greptile public docs: [Introduction](https://www.greptile.com/docs/introduction), [Graph-based codebase context](https://www.greptile.com/docs/how-greptile-works/graph-based-codebase-context), [Anatomy of a review](https://www.greptile.com/docs/code-review/first-pr-review), [Key features / TREX](https://www.greptile.com/docs/code-review/key-features), [Greptile v3 agentic review](https://www.greptile.com/blog/greptile-v3-agentic-code-review), [TREX blog](https://www.greptile.com/blog/trex-code-execution).
- GitHub docs: [About Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review), [Using Copilot code review](https://docs.github.com/copilot/using-github-copilot/code-review/using-copilot-code-review).

---

## 2. How Greptile works (product model)

### 2.1 Indexing / graph construction
Per Greptile’s documentation, when a repo is connected Greptile builds a **repository graph**:

1. **Parse** files (effectively AST-level extraction of directories, files, functions, classes, variables).
2. **Map relationships** — function calls, imports, dependencies, variable usage.
3. **Store** the graph for query during reviews.

Third-party technical writeups describing Greptile’s semantic graph additionally mention stages such as natural-language summaries of units, **embeddings** into a vector store, and edges for call/import **and** embedding similarity. Treat those as secondary descriptions of the same idea: **code is structure + retrieval, not only a text diff**.

### 2.2 Review-time behavior (v3 agentic loop)
Greptile v3 (blog, 2025-11) moved from a rigid “diff → context → comments” flowchart to an **agentic detective loop**:
- Tools such as **codebase search** and **learned rules**.
- High limits on tool use / inference so the agent can **multi-hop** (follow nested callers/callees, compare similar implementations, optionally consult git history).
- Claimed outcomes: higher upvote ratio (+256% vs v2), higher action rate, better precision via a higher “sureness” threshold.

At PR time Greptile posts (see *Anatomy of a Review*):
- **PR summary** (what changed + issues).
- **Confidence score** 0–5 (merge readiness heuristic).
- **Inline comments** with **P0/P1/P2** severity.
- Optional **diagrams** (sequence / ER / class / **flow**)—selected by change type.
- Suggested fixes, “Fix with your Agent,” learning via 👍/👎.

### 2.3 Optional tools Greptile can use (and whether we saw them)

| Capability | What it is | Observed on PRs #1–#3? |
|------------|------------|-------------------------|
| Graph / codebase index queries | Cross-file callers, imports, patterns | **Strongly indicated** (see §7) |
| Codebase search (agentic v3) | Multi-hop file reads beyond the diff | **Strongly indicated** (outside-diff comment; cross-module API contracts) |
| Learned team rules / memory | Adapt from reactions & PR discussion | **Not evidenced** (fresh experiment; no training loop) |
| Custom `greptile.json` / `.greptile/` rules | Org standards | **Not configured** in this repo |
| Cross-repo clusters | Multi-repo context | **N/A** |
| **TREX** (Test, Run, EXecute) | Sandbox: write/run tests, attach logs/screenshots | **Not observed** — no sandbox artifacts, no runtime proof comments |
| MCP / Fix-with-Agent buttons | IDE remediation path | Present as product UX; not part of our analysis |

**Conclusion on tool use in this experiment:** Greptile behaved like **static agentic + graph/search review**. It did **not** appear to exercise TREX. The most “tool-like” artifacts we *did* see are **Mermaid flowcharts of missing edges** and an **outside-diff** comment—both consistent with call-graph traversal rather than hunk-only linting.

### 2.4 Pricing context (for buy decision)
Public Greptile site (as of research): Starter free (limits), Pro ~$30/seat/month with credit model; TREX reviews cost more credits than standard reviews. Exact billing should be confirmed in-app.

---

## 3. How Copilot review works (product model vs this experiment)

### 3.1 GitHub Copilot code review (the intended baseline)
From GitHub docs:
- Reviews PRs (and IDE selections) for bugs, security, style; posts **Comment** reviews (never Approve / Request changes—**does not satisfy** required approvals).
- Trigger: assign Copilot as reviewer, or auto-review policies; CLI `gh pr edit --add-reviewer`.
- Typical latency claimed ~tens of seconds for a pass.
- **Effort levels:** Lite (fast/common issues) vs Balanced (higher-reasoning, more AI credits, better for complex/cross-service).
- **Agentic capabilities:** “full project context gathering” via GitHub Actions runners; can pass suggestions to Copilot cloud agent; can use **agent skills** and **MCP servers** when configured.
- Consumes **AI credits**; Actions minutes for agentic context.
- Excludes some file types (lockfiles, logs, SVG, …).

GitHub Copilot **did not run** here (credits / access). Its documented “full project context” is conceptually closer to Greptile than people assume for older Copilot, but Greptile’s differentiator remains the **persistent repo graph + always-on bot + diagrams/confidence + optional TREX**.

### 3.2 Copilot in *this* report = Cursor Bugbot
Cursor’s Bugbot review subagent:
- Computes a local git diff (`branch changes` vs base `main`).
- Reasons over that diff (and can read files) to emit severity-tagged findings with file:line locations.
- Does **not** post to GitHub automatically in our workflow.
- Does **not** expose Greptile-style confidence scores or Mermaid diagrams.
- In practice for this repo, it performed **cross-file integration reasoning** similar in spirit to Greptile’s missing-edge findings—i.e., it was **not** limited to pure style nits.

When this report says Copilot “reviewed X,” it means Bugbot analyzed the `main...develop-N` diff and produced the finding tables in §6.

---

## 4. Code changes that were made (inventory)

### 4.1 Small tier — `develop-1` (`c82a6cf1`) — +93 / −8

| File | Role of change |
|------|----------------|
| `main.py` | Bare `BLE` returns fresh-run args; `--resume` now passes **resolved absolute** path |
| `mutations.py` | Optional dictionary tokens; `dictionary_insert`; `splice`; strategy hit counters; wired into `random_mutation` |
| `simple_fuzzer2.py` | Crash-hot havoc intensity bias; occasional same-path seed splice |

**Crux:** Improve mutation diversity + fix BLE CLI/resume ergonomics without redesigning the fuzzer architecture.

**Pre-existing code touched:** Interactive CLI BLE branch; `MutationEngine` strategies; HTTP mutation intensity selection near `SeedQ` / `crash_correlation`.

### 4.2 Medium tier — unique on `develop-2` (`ce356ed1`) — +525 / −13 on top of small

| File | Role of change |
|------|----------------|
| `power_schedule.py` (**new**, 249 LOC) | AFL-like modes (explore/exploit/COE/fast/…); `SeedStats`; `calculate_energy`; summaries |
| `ble_energy.py` (**new**, 144 LOC) | `BLEEnergyScheduler`, transition helpers, `splice_sequences` |
| `dictionaries/http_api.dict` (**new**) | HTTP/API tokens |
| `mutations.py` | `from_dictionary_file` AFL dict loader |
| `simple_fuzzer2.py` | Load dict file; construct `PowerSchedule`; blend schedule into energy; persist `power_schedule.json` |
| `BLE/Smartlock.py` | Import scheduler; interesting-byte mut; donor-capable `mutate_input`; `assign_energy`/`choose_next` use scheduler |

**Crux:** Add dedicated scheduling subsystems for HTTP + BLE and load richer dictionaries—**but** BLE feedback/`record` and donor splice must be connected for the feature to work.

**Pre-existing code:** BLE campaign loop (`afl_fuzz`), HTTP `assign_energy` / `update_energy_metrics`, mutation engine.

### 4.3 Large tier — unique on `develop-3` (`6a2233a3`) — +1821 / −9 on top of medium

| File | Role of change |
|------|----------------|
| `corpus_manager.py` (**new**, 316) | Weighted corpus, favoritism, persistence, selection APIs |
| `coverage_bitmap.py` (**new**, 252) | HTTP outcome “edges,” interestingness scores |
| `crash_triage.py` (**new**, 292) | Crash signatures / dedup / optional minimize |
| `fuzz_stats.py` (**new**, 208) | Campaign counters; **requires `reveals_bug and bug_id`** to count crashes |
| `havoc_stage.py` (**new**, 202) | Stacked havoc mutations |
| `seed_minimizer.py` (**new**, 198) | Structural trim with interestingness predicate |
| `session_replay.py` (**new**, 217) | Replay helpers + HTML report |
| `simple_fuzzer2.py` | Wire all of the above into metrics, sessions, mutation path |

**Crux:** Stand up a full greybox pipeline (corpus, coverage, triage, stats, havoc, minimize, report). Success hinges on **plumbing** request results and bug IDs into telemetry and on **honest** minimizer predicates—plus actually **selecting** from the new corpus.

**Pre-existing code:** Main HTTP fuzz loop, `SeedQ`-based `choose_next_seed`, `update_energy_metrics`, session save paths.

---

## 5. What Greptile reviewed and said (verbatim essence)

### 5.1 PR #1 (small) — confidence 5/5
**Summary understanding (accurate):** Expands AFL-style mutations; adjusts BLE command handling; bare `BLE`; resolved resume paths; dictionary insert; splice; strategy telemetry; crash-associated intensity; occasional same-path splice.

**Inline defects:** none.

**Did Greptile get the crux?** **Yes.** It recognized refinements, not a rewrite, and correctly treated the PR as merge-safe.

**Compared to “normal” review volume:** Low comment count is **appropriate** (clean small PR)—not under-reviewing.

### 5.2 PR #2 (medium) — confidence 2/5
**Summary understanding (accurate):** AFL-inspired HTTP/BLE scheduling, dictionary mutations, splicing, BLE resume—and **explicitly** that BLE feedback scheduling + splicing are unreachable while HTTP scheduling conflates identical payloads across endpoints.

**Inline P1s:**
1. `BLE/Smartlock.py` — **Scheduler scores stay empty** (`record` never called).
2. `power_schedule.py` — **Endpoint statistics conflated** (payload-only fingerprint).

**Outside diff:**
- `BLE/Smartlock.py:279` — **BLE splicing unreachable** (`mutate_input(seed)` omits donor).

**Mermaid flowchart:** Seed queue → choose → energy → mutate → execute → observe, with **missing BLE record** edge back to scheduler and **donor not supplied** edge into mutate.

**Did Greptile get the crux?** **Yes—better than a surface reading.** It treated “new scheduler module” as incomplete until write-path exists.

**Volume vs normal:** For ~600 LOC with 2 real integration bugs, **2 P1s + 1 outside + low confidence** is **high signal, low noise**—stronger than a typical style-heavy bot pass.

### 5.3 PR #3 (large) — confidence 2/5
**Summary understanding (accurate):** Full AFL-style corpus/coverage/scheduling/crash-triage/havoc/minimize/replay/report pipeline; integration **loses** request-result data and bug IDs before telemetry; unverified minimized payloads favored.

**Inline P1s:**
1. `simple_fuzzer2.py` — **Response telemetry loses outcomes** (`s_prime` missing fields).
2. `simple_fuzzer2.py` — **Crash identifiers dropped** (`bug_id` not passed; `FuzzStatsCollector` needs both flags).
3. `simple_fuzzer2.py` — **Minimization discards coverage behavior** (`lambda candidate: True`).

**Mermaid flowchart:** Execution → classification → `update_energy_metrics` with **result fields not copied** and **bug_id not forwarded**, then coverage/triage/stats/minimizer → favored corpus.

**Files needing attention:** `simple_fuzzer2.py`, `fuzz_stats.py`, `coverage_bitmap.py`, `crash_triage.py`, `seed_minimizer.py`, `corpus_manager.py`.

**Did Greptile get the crux?** **Yes.** It understood the pipeline *and* where integration fails.

**Volume vs normal:** 3 P1s on a 2.4k LOC PR with many new files is **selective**—it did **not** nit every new module; it focused on **integration seams**. That is “more than a shallow skim” on severity, “less than a noisy linter” on comment count.

---

## 6. What Copilot (Cursor) reviewed and said

### 6.1 PR #1 / develop-1
**Bugs:** none.  
**Alignment:** Matches Greptile’s clean verdict.  
**Minor human note:** `strategy_hits` collected but never exported (neither bot blocked on this).

### 6.2 PR #2 / develop-2

| Sev | Location | Finding |
|-----|----------|---------|
| high | `BLE/Smartlock.py` | `ble_scheduler.record()` never called |
| medium | `BLE/Smartlock.py` | donor splice never invoked |
| medium | `power_schedule.py` | stats keyed by payload fingerprint only |
| medium | call site in `simple_fuzzer2.py` | `update_energy_metrics(...)` omits `coverage_gain` → always 0 |
| low | `mutations.py` dict loader | lines with `=` and `"` misparsed as AFL `name="value"` |

Disputed/soft FP: claim that dictionary tokens never reach `mutate_payload`—actually `mutate_payload` → `random_mutation` can select `dictionary_insert`.

### 6.3 PR #3 / develop-3

| Sev | Location | Finding |
|-----|----------|---------|
| high | `simple_fuzzer2.py` | response metadata never attached to `s_prime` before coverage/triage/stats |
| high | `simple_fuzzer2.py` | `note_iteration(reveals_bug=True)` without `bug_id` → crash stats stay 0 |
| medium | `simple_fuzzer2.py` | `mark_result` treats rarity/`interesting_score` as coverage gain → favoritism doesn’t decay |
| medium | `simple_fuzzer2.py` | `CorpusManager` filled/persisted but `choose_next_seed` still uses only `SeedQ` |

---

## 7. Differential analysis: overlap, uniques, graph necessity

### 7.1 Master overlap matrix

| Finding | Tier | Greptile | Copilot | Needs graph/AST-ish reasoning? | Notes |
|---------|------|----------|---------|--------------------------------|-------|
| Clean small PR / no false bugs | S | ✓ | ✓ | No | Both calibrated |
| BLE `record` never called | M | ✓ P1 | ✓ high | **Yes (call graph)** | Classic missing write edge |
| BLE donor splice dead | M | ✓ outside | ✓ medium | **Yes (call graph)** | Caller/callee arity |
| Schedule payload-only key | M | ✓ P1 | ✓ medium | **Partial** | Data-model; readable in one file but impact is cross-endpoint |
| `coverage_gain` always 0 | M | ✗ | ✓ | **Yes (call graph)** | Callee default vs caller omission |
| Dict `=`/`"` parse corruption | M | ✗ | ✓ | No (local) | Lexer/parser nit |
| `s_prime` fields not plumbed | L | ✓ P1 | ✓ high | **Yes (dataflow)** | Loop locals → metrics → many modules |
| `bug_id` dropped / stats ∧ | L | ✓ P1 | ✓ high | **Yes (cross-module API)** | Must read `fuzz_stats.note_iteration` |
| Minimizer `lambda: True` | L | ✓ P1 | ✗ | **Partial** | Visible at call site; policy impact needs corpus favoritism context |
| Corpus never selected | L | ✗ | ✓ | **Yes (architecture)** | New type unused by selector |
| Rarity-as-gain favoritism | L | ✗ | ✓ | **Partial** | Score semantics across helpers |
| Mermaid missing-edge diagrams | M/L | ✓ | ✗ | Product feature | Explains graph narrative to humans |
| Confidence score 5→2 | all | ✓ | ✗ | Product feature | Merge UX |
| TREX runtime proof | — | ✗ | ✗ | N/A | Unused |

### 7.2 Did Greptile identify *more* than normal?
- **More severity-weighted value than a style bot:** yes on medium/large.
- **More raw comments than Copilot:** no—Copilot listed **more** medium/low items on medium tier.
- **More unique critical policy bugs:** Greptile’s minimizer finding is a standout Copilot miss.
- **Less coverage of corpus-selection dead wiring:** Copilot win.

### 7.3 Which findings *truly* need a graph / AST / multi-hop index?

**Strong graph/call-graph / dataflow character (hard with diff-only tunnel vision):**
1. BLE `record` missing while `energy_for`/`rank_queue` read state.
2. Donor argument never supplied.
3. `s_prime` dataflow hole affecting coverage + crash triage modules.
4. `bug_id` contract across classifier → metrics → `FuzzStatsCollector`.
5. Corpus module vs `choose_next_seed` still on `SeedQ` (architectural orphan).

**Identifiable from a careful single-file or local hunk read (graph helpful but not strictly required):**
1. Payload-only `seed_fingerprint` keying (local to `power_schedule.py`, impact inferred).
2. `lambda candidate: True` (local call site; Greptile excelled at stating corpus consequences).
3. Dict parser `=`/`"` heuristic (local).

**Important nuance:** Copilot (Cursor) also found (1)–(4)-class issues **without** Greptile’s hosted graph. So the experiment supports: **structural reasoning matters**, but **Greptile is not the only system capable of it**. Greptile’s differentiator in-run was **packaging** (confidence, diagrams, outside-diff), **always-on GitHub delivery**, and the **minimizer** catch—not a monopoly on cross-file bugs.

### 7.4 Evidence Greptile used graph/search tools (inferential)
We cannot see Greptile’s private tool traces, but the public artifacts strongly imply multi-hop analysis:
- Outside-diff comment at the exact `mutate_input(seed)` call while the donor parameter was introduced elsewhere.
- Explicit reference to `FuzzStatsCollector` conjunction semantics defined in another new file.
- Flowcharts drawing **absent** edges (negative space in the call graph).
- “Files needing attention” spanning six modules on PR #3.

Absence of TREX artifacts implies the agent **did not** (or could not) validate via execution.

---

## 8. Pros and cons

### 8.1 Greptile

**Pros**
- Persistent **repo graph** + agentic search designed for ripple effects.
- Always-on GitHub App: summary, **P-levels**, **confidence score**, **diagrams**.
- High signal on this repo’s medium/large PRs; low false-positive rate on small.
- Learning system, custom rules, MCP, Fix-with-Agent, optional **TREX** (not used here).
- Explains *downstream impact* (e.g., “reports show zero crashes”).

**Cons**
- Paid SaaS (credits/seats); cost stacks with TREX.
- Missed several real issues Copilot found (coverage_gain arg, corpus unused, rarity-as-gain, dict parse).
- Summary sometimes paraphrases paths/commit titles.
- Dense HTML summaries; outside-diff easy to miss.
- Without TREX, still “smart static”—can be wrong confidently.
- Overlap with modern agentic Copilot/Cursor reduces uniqueness.

### 8.2 Copilot (Cursor stand-in) / GitHub Copilot product notes

**Pros (Cursor as used)**
- Matched Greptile on most critical integration bugs.
- Found additional wiring/semantic defects.
- Already in the IDE workflow; no extra PR bot seat for this path.
- Flexible base-branch reviews for local branches.

**Cons (Cursor as used)**
- Not automatic on GitHub PRs in our setup (process friction).
- No confidence score / flowchart packaging for stakeholders.
- Missed minimizer `lambda: True`.
- One soft false direction on dictionary usage.
- Findings live in chat unless manually transcribed (as we did into REPORT.md).

**GitHub Copilot product (not run) — expected pros/cons from docs**
- Pros: native PR reviewer, one-click suggestions, Lite/Balanced, growing project-context/MCP/skills, cloud-agent fix PRs.
- Cons: credits cost; Comment-only (no merge gate); quality varies; historically weaker than dedicated graph bots on deep multi-hop—but 2026 docs claim fuller project context, so **head-to-head remains unfinished** until credits return.

---

## 9. End-to-end narrative (what happened)

1. **Baseline:** Mature AFL-Fuzzer codebase with HTTP + BLE fuzz loops.
2. **Small PR:** Mutation + BLE CLI polish. Both reviewers: **safe**. Greptile 5/5.
3. **Medium PR:** New schedulers + dict. Both reviewers: **BLE feedback/splice unwired**, **schedule key collision**. Greptile 2/5 + diagram. Copilot adds coverage_gain + dict parse.
4. **Large PR:** New greybox pipeline partially wired. Both: **telemetry/`bug_id` holes**. Greptile: minimizer predicate. Copilot: corpus unused + favoritism decay. Greptile 2/5 + diagram.
5. **GitHub Copilot:** blocked.
6. **Buy framing:** Greptile proved its **graph-shaped** value proposition on *this* fuzzer, but Cursor already captures much of that value when an engineer actually runs a thorough review.

---

## 10. Recommendation

| Question | Answer |
|----------|--------|
| Did Greptile understand the crux? | **Yes** at all three tiers |
| Did it identify more than a normal noisy bot? | **Yes on severity/signal**; not on raw comment count |
| Did it identify graph/AST-hard bugs? | **Yes** (missing edges, cross-module contracts); Copilot found many of the same |
| Did it use advanced tools (TREX)? | **No evidence of TREX**; strong evidence of search/graph reasoning + diagrams |
| Worth paying vs no automation? | **Yes** for medium/large multi-file work |
| Worth paying vs Copilot/Cursor already in use? | **Situational** — buy for always-on GitHub UX + diagrams/confidence + occasional unique catches; don’t expect exclusive access to cross-file bugs |
| Next experiment | Re-enable **GitHub Copilot** Balanced reviews on the same PRs; optionally enable **TREX** and re-diff |

### Practical guidance
- **Keep Greptile** if the team wants unattended PR gates and stakeholder-readable summaries.
- **Skip / defer Greptile** if every PR already gets a Cursor/Bugbot (or GitHub Copilot Balanced) pass and budget is tight—accept the risk of missing packaging + occasional uniques like the minimizer bug.
- **Fix the shared P1/high findings** on `develop-3` before merging any tier to `main`.

---

## 11. Appendix A — Confidence & counts

| PR | Greptile confidence | Greptile inline P1 | Greptile outside | Copilot high | Copilot med | Copilot low |
|----|---------------------|--------------------|------------------|--------------|-------------|-------------|
| #1 | 5/5 | 0 | 0 | 0 | 0 | 0 |
| #2 | 2/5 | 2 | 1 | 1 | 4 | 1 |
| #3 | 2/5 | 3 | 0 | 2 | 2 | 0 |

## 12. Appendix B — Code SHAs

| Artifact | SHA |
|----------|-----|
| Small code | `c82a6cf196bb3d1bfe4434088ce1092784db85d8` |
| Medium code | `ce356ed1471c78092f0c05769c7c780d064b0163` |
| Large code | `6a2233a35474118cac65ec89940e45996e2c93ec` |

## 13. Appendix C — Status stamp
- **Date:** 2026-08-26  
- **Greptile:** complete on PRs #1–#3  
- **GitHub Copilot product:** unavailable  
- **Copilot (Cursor Bugbot):** complete on all three diffs  
- **TREX:** not observed  
- **Report revision:** comprehensive rewrite after product-doc research + full finding matrix  

## 14. Appendix D — Primary references
1. https://www.greptile.com/docs/introduction  
2. https://www.greptile.com/docs/how-greptile-works/graph-based-codebase-context  
3. https://www.greptile.com/docs/code-review/first-pr-review  
4. https://www.greptile.com/docs/code-review/key-features  
5. https://www.greptile.com/blog/greptile-v3-agentic-code-review  
6. https://www.greptile.com/blog/trex-code-execution  
7. https://docs.github.com/en/copilot/concepts/agents/code-review  
8. https://docs.github.com/copilot/using-github-copilot/code-review/using-copilot-code-review  


---

## 15. Appendix E — Verbatim Greptile summaries (captured)

### E.1 PR #1 summary (essence)
> The PR expands AFL-style mutation behavior and adjusts BLE command handling.
> - Accepts bare `BLE` invocations and passes validated resume files as resolved paths.
> - Adds dictionary insertion, payload splicing, and mutation-strategy telemetry.
> - Increases mutation intensity for crash-associated endpoints and occasionally splices same-path corpus seeds.
>
> **Confidence Score: 5/5** — appears safe to merge; BLE entry-point changes match the downstream loader contract; new mutation/crash-bias paths operate on established seed and correlation data shapes.

### E.2 PR #2 summary (essence)
> The PR adds AFL-inspired HTTP and BLE scheduling, dictionary-backed mutations, cross-seed splicing, and reliable BLE resume-path handling. The BLE integration leaves both feedback-based scheduling and splicing unreachable, while HTTP scheduling conflates identical payloads across endpoints.
>
> **Confidence Score: 2/5** — should not merge until BLE scheduling/splicing connected and HTTP schedule state isolated by endpoint.
>
> BLE campaign outcomes never populate the scheduler, its splice branch never receives a donor, and identical HTTP payloads share scheduling history across unrelated paths and methods.
>
> **Files needing attention:** `BLE/Smartlock.py`, `power_schedule.py`

**Inline P1 — Scheduler scores stay empty** (`BLE/Smartlock.py`):
> During every BLE campaign, `assign_energy` and `choose_next` read from the scheduler without any execution path calling `ble_scheduler.record`, causing energy to remain length-only and queue weights to receive no novelty or crash boosts.

**Inline P1 — Endpoint statistics are conflated** (`power_schedule.py`):
> When the same payload is scheduled for multiple paths or methods, `ensure_stats` uses only the payload fingerprint as its key, causing executions, coverage, crashes, and energy decay from one endpoint to affect another while summary metadata remains tied to the first endpoint.

**Outside diff — BLE splicing unreachable** (`BLE/Smartlock.py:279`):
> The campaign's only `mutate_input` call omits the donor argument, leaving it as `None` and preventing the new splice guard from ever passing.

### E.3 PR #3 summary (essence)
> This PR adds an AFL-style corpus, coverage, scheduling, crash-triage, havoc, minimization, replay, and reporting pipeline and integrates it with the HTTP and BLE fuzzers. The integration currently loses request-result data and bug identifiers before telemetry, and records unverified minimized payloads as favored coverage seeds.
>
> **Confidence Score: 2/5** — not safe to merge until request outcomes and bug identifiers reach telemetry and minimized corpus entries are validated.
>
> **Files needing attention:** `simple_fuzzer2.py`, `fuzz_stats.py`, `coverage_bitmap.py`, `crash_triage.py`, `seed_minimizer.py`, `corpus_manager.py`

**Inline P1 — Response telemetry loses outcomes:**
> `update_energy_metrics` reads `status_code`, `response_body`, and `error` from `s_prime`, but the request loop never copies its local result values there. This collapses every outcome for a path and method into the same `ERR`/`none` coverage bucket…

**Inline P1 — Crash identifiers are dropped:**
> …calls `note_iteration` without `bug_id`. Because `FuzzStatsCollector` records crashes only when both `reveals_bug` and `bug_id` are set, the generated statistics and campaign report show zero total and unique crashes…

**Inline P1 — Minimization discards coverage behavior:**
> …unconditional `lambda candidate: True` lets the minimizer accept every structural deletion without verifying that coverage is preserved. The reduced payload is then persisted as a favored, higher-scored corpus entry…

---

## 16. Appendix F — Graph-hop reconstruction (why these are “graph” bugs)

This section reconstructs the *minimum* reasoning hops a reviewer (human or agent) must take. Greptile’s product thesis is that a prebuilt graph + search makes these hops cheap and reliable.

### F.1 BLE `record` missing (medium)
1. See `BLEEnergyScheduler.record` / `energy_for` / `rank_queue` definitions in `ble_energy.py`.
2. See `assign_energy` → `ble_scheduler.energy_for` and `choose_next` → `rank_queue` in `Smartlock.py`.
3. Search all references to `ble_scheduler.record` / `observe_transition` in the campaign.
4. Observe **zero write-path calls** inside `afl_fuzz`.
5. Conclude energy novelty/crash terms never move → length-only behavior.

Without step 3–4 (repo-wide reference search / call graph), a diff-only reader who only opens `ble_energy.py` may think the feature is complete.

### F.2 Donor splice dead (medium)
1. See `mutate_input(seed, donor=None)` and `if donor is not None and random.random() < 0.2`.
2. Find call sites of `mutate_input`.
3. Only call is `mutate_input(seed)` → donor always `None`.
4. Feature unreachable.

This is a one-hop caller check—graph helps; grepping also works. Greptile’s **outside-diff** placement shows it inspected the call site even when commenting relative to the broader PR narrative.

### F.3 `s_prime` telemetry hole (large)
1. In `update_energy_metrics`, see reads of `s_prime["status_code"]` / `response_body` / `error`.
2. See those values fed into `coverage_bitmap.observe` and `crash_triage.record`.
3. Jump to the HTTP request loop that constructs `s_prime`.
4. Observe locals for status/body/error are **never assigned** onto `s_prime` before the call.
5. Infer collapsed coverage buckets and merged crash signatures.

This is multi-module **dataflow**, Greptile’s advertised strength. Copilot found the same.

### F.4 `bug_id` ∧ `reveals_bug` (large)
1. See classifier producing a bug id in the loop.
2. See `update_energy_metrics` / `note_iteration` call **without** `bug_id=`.
3. Open `fuzz_stats.py` and read `if reveals_bug and bug_id:`.
4. Conclude reports undercount crashes to zero.

Requires reading a **new file’s API contract** not visible in the call-site hunk alone—index/search helps.

### F.5 Minimizer `lambda: True` (large) — Greptile unique
1. See `seed_minimizer.trim(..., still_interesting=lambda candidate: True)`.
2. Understand `SeedMinimizer` accepts deletions whenever predicate returns true.
3. See trimmed seed `corpus.add(..., favored=True, weight=1.7)`.
4. Conclude favored corpus polluted with unverified shrinks.

Copilot missed this. Possible reasons: attention on telemetry holes; predicate looks “intentionally structural” without following corpus favoritism policy. Greptile explicitly tied predicate → favored corpus—**policy graph**, not syntax.

### F.6 Corpus unused (large) — Copilot unique
1. See `CorpusManager` constructed, `add`/`mark_result`/`save` used.
2. Read `choose_next_seed` end-to-end.
3. Observe only `SeedQ` / legacy weights—no `corpus.choose` (or equivalent).
4. Conclude architectural orphan.

Greptile listed `corpus_manager.py` under “files needing attention” but did **not** emit this specific P1. Copilot did.

---

## 17. Appendix G — What “normal” review would look like vs what we got

| Review style | Typical output on these PRs | What we observed |
|--------------|-----------------------------|------------------|
| Style/linter bot | Naming, imports, line length | **Neither** Greptile nor Copilot spammed style |
| Diff-only LLM skim | Restate PR; maybe local null checks | Greptile/Copilot went deeper |
| Careful human senior review | Likely catch unwired BLE + telemetry; maybe miss one of minimizer/corpus | Matches combined bot union |
| Greptile alone | Integration P1s + diagrams + confidence | Observed |
| Copilot alone | Integration highs + extras; no diagrams | Observed |
| Greptile + TREX (hypothetical) | Possibly runtime proof that stats stay zero / energy never changes | **Not observed** |

**Interpretation:** For this experiment, Greptile performed like a **strong senior static reviewer with call-graph habits**, not like a nitpicking style bot. Copilot performed similarly on defect finding, weaker on stakeholder packaging, stronger on a couple of orphans.

---

## 18. Appendix H — Limitations of this study
1. **GitHub Copilot product absent** — Cursor stand-in may over- or under-estimate GitHub Copilot Balanced.
2. **No TREX** — cannot judge Greptile’s execution differentiator.
3. **Single codebase / domain** (Python fuzzers)—graph value may differ for monorepos/polyglot services.
4. **Authors of the buggy wiring were agents** — defects are realistic integration bugs but not organic human mistakes.
5. **No user 👍/👎 training window** — Greptile learning system unused.
6. **Inference of tool use** — no access to Greptile’s private agent traces; evidence is behavioral.
7. REPORT commits on branches slightly shift tip SHAs after code SHAs under review.

---

## 19. Appendix I — Buy decision checklist

Use this checklist when deciding whether to pay for Greptile given Copilot/Cursor:

- [ ] Do we need **unattended** reviews on every GitHub PR?
- [ ] Do PMs/leads want **confidence scores + diagrams** without opening an IDE?
- [ ] Are most bugs we fear **cross-file integration** bugs?
- [ ] Will we enable **TREX** (otherwise missing Greptile’s runtime wedge)?
- [ ] Is Cursor/GitHub Copilot Balanced **already mandatory** on every PR?
- [ ] Is $ / seat / credit burn acceptable for marginal unique catches (~minimizer-class)?

**If the first three are yes and TREX will be enabled → pay.**  
**If Cursor review is already mandatory and budget is tight → defer; re-evaluate after GitHub Copilot Balanced head-to-head.**
