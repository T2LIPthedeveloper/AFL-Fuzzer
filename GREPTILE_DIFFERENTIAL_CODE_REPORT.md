# GREPTILE_DIFFERENTIAL_CODE_REPORT.md

## Does Greptile’s graph logic provide additional benefit worth paying for?

**Short answer:** **Mostly yes for medium/large multi-file fuzzer work—with nuance.** Greptile delivered strong cross-file findings on PRs #2 and #3. GitHub Copilot did not run (credits / collaborator 422). **Cursor Bugbot** was used as the standard automated reviewer stand-in and **substantially overlapped** Greptile on the highest-severity dataflow bugs, while each tool still found unique issues. Greptile remains worth paying for if you value merge confidence scores, pipeline diagrams, and policy/predicate bugs; it is **not** uniquely required to catch every integration defect a modern agent review can find.

---

## Experiment setup

| Tier | Branch | PR | LOC vs `main` | Code head |
|------|--------|----|---------------|-----------|
| Small | `develop-1` | [#1](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/1) | +93 / −8 | `c82a6cf1…` |
| Medium | `develop-2` | [#2](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2) | +618 / −21 | `ce356ed1…` |
| Large | `develop-3` | [#3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/3) | +2432 / −23 | `6a2233a3…` |

All PRs target `main`. Changes are additive AFL-greybox improvements (mutations → power schedule → corpus/coverage/triage/havoc/minimize/report).

Per-PR detail: `REPORT.md` on each `develop-*` branch.

---

## Reviewer participation

| PR | Greptile | Copilot | Cursor Bugbot (stand-in) |
|----|----------|---------|--------------------------|
| #1 Small | Yes — 5/5, 0 inline | **No** | Yes — **0 bugs** |
| #2 Medium | Yes — 2/5, 2 P1 + outside-diff | **No** | Yes — 1 high + 4 medium + 1 low |
| #3 Large | Yes — 2/5, 3 P1 | **No** | Yes — 2 high + 2 medium (+ inherits #2) |

**Blocker for Copilot:** credits exhausted / `copilot-pull-request-reviewer` HTTP 422 (not a collaborator).

---

## Collated findings by tier

### Small (#1)
| Greptile | Cursor Bugbot |
|----------|---------------|
| Contract-aware BLE CLI ↔ harness path reading; no false positives | No bugs (aligned) |
| Confidence 5/5 | No merge score |

**Verdict:** Tie. Greptile adds little beyond a clean skim on <100 LOC.

### Medium (#2) — high graph signal
| Finding | Greptile | Cursor |
|---------|----------|--------|
| BLE `record()` never called | Yes (P1) | Yes (high) |
| BLE splice donor never passed | Yes (outside-diff) | Yes (medium) |
| Schedule keyed by payload only | Yes (P1) | Yes (medium) |
| `coverage_gain` always 0 at call site | **No** | Yes (medium) |
| Dict loader corrupts `=`+`"` tokens | **No** | Yes (low) |
| Mermaid missing-edge flowchart | Yes | No |

**Verdict:** Strong overlap on the core integration bugs. Cursor found additional call-site / parser issues; Greptile’s flowchart and low confidence score aid triage.

### Large (#3) — highest graph signal
| Finding | Greptile | Cursor |
|---------|----------|--------|
| `s_prime` telemetry not plumbed | Yes (P1) | Yes (high) |
| `bug_id` dropped → zero crash stats | Yes (P1) | Yes (high) |
| Minimizer `lambda: True` | Yes (P1) | **No** |
| Corpus never drives `choose_next_seed` | **No** | Yes (medium) |
| `mark_result` rarity treated as gain | **No** | Yes (medium) |
| Pipeline mermaid | Yes | No |

**Verdict:** Both catch the critical telemetry holes. Greptile uniquely flags the minimizer policy bug; Cursor uniquely flags corpus dead-wiring and favoritism decay.

---

## Unique vs overlapping (updated)

### Greptile uniquely observed
- Minimizer `lambda: True` → favored corpus pollution
- Merge confidence scores (5/5 vs 2/5) calibrated to issue severity
- Mermaid campaign/pipeline diagrams of missing edges
- Explicit “not merge-safe” narrative with downstream impact

### Cursor Bugbot uniquely observed
- `coverage_gain` omitted at `update_energy_metrics` call site (medium tier)
- Dictionary parser mis-handling of tokens containing `=` and `"`
- Corpus populated but never selected for fuzzing
- `mark_result` using rarity score as perpetual coverage gain

### Overlap (both)
- Unwired BLE feedback / splice donor
- Power-schedule fingerprint collisions across endpoints
- Request result fields not copied into `s_prime`
- `bug_id` not forwarded to stats collector

### Copilot uniquely observed
- **None** (unavailable)

---

## Benefits and pitfalls

### Greptile — benefits
1. Integration-bug detection with impact narratives
2. Calibrated confidence scores
3. Visual missing-edge diagrams
4. Caught policy/predicate bug Cursor missed (`lambda: True`)

### Greptile — pitfalls
1. Missed some wiring issues Cursor found (corpus selection, coverage_gain arg, dict parse)
2. Paraphrased names/paths; dense HTML summaries
3. Weaker ROI on tiny clean PRs
4. Paid product vs Cursor already in the IDE workflow

### Cursor Bugbot — benefits
1. Matched Greptile on most high-severity dataflow bugs without Greptile’s index
2. Strong at “API exists but never called” and semantic favoritism bugs
3. No extra SaaS cost if Cursor is already licensed

### Cursor Bugbot — pitfalls
1. Missed minimizer interestingness predicate
2. No confidence / merge recommendation packaging for GitHub PR UX
3. Manual orchestration per branch (not a always-on PR bot here)

### Copilot
- Unevaluable in this run due to credits/access.

---

## Recommendation

| Question | Answer |
|----------|--------|
| Does Greptile graph logic add value? | **Yes**, especially diagrams + confidence + policy bugs |
| Worth paying for vs *no* automated review? | **Yes** |
| Worth paying for vs Cursor Bugbot specifically? | **Marginal / situational** — heavy overlap on critical bugs; Greptile wins on PR bot UX + minimizer catch; Cursor wins on a few wiring issues and zero incremental cost if already subscribed |
| Worth paying for vs Copilot specifically? | **Still inconclusive** until Copilot runs |
| Best use of Greptile | Always-on GitHub reviews for multi-file refactors/pipelines |
| Weak use | Tiny clean PRs; teams already running thorough Cursor/agent review on every PR |

### Concrete next steps
1. Optionally enable Copilot when credits return and append a third column
2. Fix shared P1/high findings on `develop-3` as a remediation PR to validate review quality
3. Keep per-PR `REPORT.md` files as the audit trail

---

## Status stamp
- **Date:** 2026-08-26  
- **Greptile:** complete on all three PRs  
- **Copilot:** not received (credits/access)  
- **Cursor Bugbot:** complete on all three diffs as standard stand-in  
- **Collated by:** follow-up after [Tiered Greptile PR experiment](89f134f8-de5b-42c4-99e4-92f3bbad1714) + Cursor review pass  
