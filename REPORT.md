# REPORT.md — PR #2 (Medium tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2  
**Branch:** `develop-2` → `main`  
**Tier:** MEDIUM (~500–600 LOC including small-tier base)  
**Head SHA:** `ce356ed1471c78092f0c05769c7c780d064b0163`  
**LOC vs main:** +618 / −21  

## Experiment context

Second rung of the Greptile vs GitHub Copilot (standard) comparison ladder. Contains all `develop-1` changes **plus** medium-tier power scheduling and BLE energy helpers.

### Code changes in this tier (additive on small)
- `power_schedule.py` — Fast/Explore/Exploit/COE-style energy assignment
- `ble_energy.py` — BLE sequence energy + queue ranking + splice helper
- `dictionaries/http_api.dict` — HTTP/API dictionary tokens
- Wire power schedule into `simple_fuzzer2.py` energy assignment / session snapshot
- BLE `Smartlock.py` integration of scheduler, donor splice, interesting-byte mutations

## Reviewer status

| Reviewer | Status | Notes |
|----------|--------|-------|
| **Greptile** | Received | Summary + **2 inline P1s** + 1 outside-diff note; confidence **2/5** |
| **GitHub Copilot** | **Not received** | Same access blocker as PR #1 |

## What Greptile found

### Summary (confidence 2/5)
- Accurately described AFL-inspired HTTP/BLE scheduling, dictionary mutations, splicing, and BLE resume-path handling
- Flagged that BLE feedback scheduling / splicing are **not fully wired into the campaign loop**
- Flagged that HTTP schedule state can **conflate identical payloads across endpoints**

### Inline findings (unique graph / cross-file style)
1. **`BLE/Smartlock.py` — Scheduler scores stay empty (P1)**  
   Greptile traced that `assign_energy` / `choose_next` read scheduler state but no campaign path calls a `record`-style feedback API, so energy stays length-only.  
   **Why this is graph-like:** requires following call graph from campaign loop → scheduler API → missing write edge.

2. **`power_schedule.py` — Endpoint statistics conflated (P1)**  
   Fingerprint keyed only on payload, so the same body on different path/method pairs shares execution/crash/energy history.  
   **Why this is graph-like:** data-model / keying insight across schedule consumers, not a local syntax issue.

### Outside-diff note
- **BLE splicing unreachable:** campaign `mutate_input` call omits donor argument, so splice guard never fires.

### Mermaid flowchart
Greptile emitted a campaign flowchart highlighting the missing BLE record edge and missing donor edge — useful for explaining integration gaps.

## What Copilot found

**Pending / unavailable** (Copilot PR reviewer not enabled / not a collaborator). Skeleton for when it arrives:

| Expected Copilot focus (hypothesis) | Status |
|-------------------------------------|--------|
| Local style / null checks in new modules | Not observed |
| Missing type hints / docstring nits | Not observed |
| Possibly miss cross-file “record never called” bug | — |

### Next steps
Enable Copilot code review on the repo, re-request on PR #2, then append Copilot findings and recompute overlap.

## Overlap
- N/A (Copilot silent)

## Pitfalls and benefits (this tier)

### Greptile — benefits
- **Caught real integration bugs** (unwired feedback, missing donor, weak schedule keys) that line-local review often misses
- Flowchart made the missing edges obvious
- Confidence score correctly low (2/5) given those gaps

### Greptile — pitfalls
- Some summary path names / commit titles are slightly paraphrased vs exact repo filenames
- Outside-diff comments can be easy to miss in the GitHub UI

### Copilot
- Still unevaluable here; comparison incomplete for this PR

## Verdict for medium PRs
Greptile’s graph/call-flow reading provided clear additional value: it treated “feature added but not connected” as a first-class defect. That class of finding is a strong argument for Greptile on multi-file fuzzer refactors—**if** Copilot later only reports local issues, Greptile wins this tier.
