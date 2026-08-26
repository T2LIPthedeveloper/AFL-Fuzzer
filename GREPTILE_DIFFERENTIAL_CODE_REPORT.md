# GREPTILE_DIFFERENTIAL_CODE_REPORT.md

## Does Greptile’s graph logic provide additional benefit worth paying for?

**Short answer:** **Yes, for medium and large multi-file fuzzer changes—based on Greptile results alone.** Copilot (standard) reviews did **not** arrive on this repository during the experiment window, so the commercial “vs Copilot” claim is **partially blocked**. Even so, Greptile demonstrated clear **cross-file / call-graph / dataflow** findings that are exactly the class of issues line-local review tends to miss.

---

## Experiment setup

| Tier | Branch | PR | LOC vs `main` | Head (code, pre-REPORT) |
|------|--------|----|---------------|-------------------------|
| Small | `develop-1` | [#1](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1) | +93 / −8 | `c82a6cf1…` |
| Medium | `develop-2` | [#2](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2) | +618 / −21 | `ce356ed1…` |
| Large | `develop-3` | [#3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3) | +2432 / −23 | `6a2233a3…` |

All PRs target `main`. Changes are additive AFL-greybox improvements (mutations → power schedule → corpus/coverage/triage/havoc/minimize/report).

Per-PR detail: `REPORT.md` on each `develop-*` branch.

---

## Reviewer participation

| PR | Greptile | Copilot (standard) |
|----|----------|---------------------|
| #1 Small | Yes — summary, confidence 5/5, 0 inline | **No** |
| #2 Medium | Yes — summary, confidence 2/5, 2 inline P1 + outside-diff | **No** |
| #3 Large | Yes — summary, confidence 2/5, 3 inline P1 | **No** |

**Blocker:** Requesting `copilot-pull-request-reviewer` returned HTTP 422 (not a collaborator). `@copilot` comments did not produce bot reviews. Org/repo likely lacks Copilot **code review** enablement.

---

## Collated Greptile findings

### Small (#1)
- Understood BLE CLI ↔ harness path contract
- No false-positive defect spam on a clean small PR
- **Graph bonus:** light but real (contract consistency)

### Medium (#2) — high graph signal
| Finding | Type | Why graph-ish |
|---------|------|----------------|
| BLE scheduler never `record`s campaign outcomes | Missing write edge in call graph | Follows campaign loop → scheduler API |
| BLE splice donor never passed | Dead feature / unreachable branch | Caller/callee wiring across functions |
| Power-schedule stats keyed only by payload | Cross-endpoint state conflation | Data-model keying affecting multiple consumers |

### Large (#3) — highest graph signal
| Finding | Type | Why graph-ish |
|---------|------|----------------|
| Request results not copied into `s_prime` before metrics | Dataflow hole | Loop locals ↔ metrics helper ↔ coverage/crash modules |
| `bug_id` not forwarded; stats require `reveals_bug ∧ bug_id` | Cross-module API contract | Classifier → metrics → `fuzz_stats` |
| Minimizer uses `lambda: True` then favors corpus entries | Predicate / policy bug | Minimizer ↔ corpus favoritism |

---

## Unique vs overlapping (as of this report)

### Greptile uniquely observed (vs absence of Copilot)
- Unwired BLE feedback / splice donor
- Schedule fingerprint collisions across endpoints
- Telemetry field plumbing gap
- Crash ID drop causing zeroed campaign crash counts
- Invalid interestingness predicate on minimize → favored corpus pollution
- Pipeline mermaid diagrams of missing edges

### Copilot uniquely observed
- **None yet** (no reviews)

### Overlap
- **None yet**

---

## Benefits and pitfalls

### Greptile — benefits
1. **Integration-bug detection** on medium/large PRs (the valuable part of “graph” review)
2. **Calibrated confidence scores** (5/5 small, 2/5 medium/large with real issues)
3. **Impact narrative** (e.g., reports will show zero crashes)
4. Fast automated turnaround via GitHub App check + summary comment

### Greptile — pitfalls
1. Summary prose sometimes paraphrases names/paths
2. Outside-diff comments easy to overlook
3. Dense HTML `<details>` summaries less readable than pure inline threads
4. Cost only justified when PRs span modules (small PR added little beyond a careful human skim)

### Copilot — benefits / pitfalls
- **Unknown in this run.** Next step is enable Copilot code review and re-diff findings against the Greptile set above.

---

## Recommendation

| Question | Answer |
|----------|--------|
| Does Greptile graph logic add value? | **Yes** on this codebase for medium/large greybox work |
| Worth paying for vs no automated review? | **Yes** |
| Worth paying for vs Copilot specifically? | **Inconclusive until Copilot runs**; hypothetically yes if Copilot stays hunk-local |
| Best use | Multi-file refactors, new pipelines, telemetry wiring |
| Weak use | Tiny clean PRs (diminishing returns) |

### Concrete next steps
1. Enable GitHub Copilot code review on `T2LIPthedeveloper/AFL-Fuzzer`
2. Re-request reviews on PRs #1–#3 (or open follow-up commits)
3. Update each `REPORT.md` + this collated file with Copilot rows and an overlap matrix
4. Optionally fix Greptile’s P1s on `develop-3` as a separate “remediation” PR to validate review quality

---

## Status stamp
- **Date:** 2026-08-26  
- **Greptile:** complete on all three PRs  
- **Copilot:** not received — reports intentionally left with placeholders  
- **Collated by:** autonomous agent run in AFL-Fuzzer workspace  
