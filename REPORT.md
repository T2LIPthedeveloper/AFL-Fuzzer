# REPORT.md — PR #2 (Medium tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2  
**Branch:** `develop-2` → `main`  
**Tier:** MEDIUM (~500–600 LOC including small-tier base)  
**Head SHA (code):** `ce356ed1471c78092f0c05769c7c780d064b0163`  
**LOC vs main:** +618 / −21  

## Experiment context

Second rung of the Greptile vs standard reviewer ladder. Contains all `develop-1` changes **plus** medium-tier power scheduling and BLE energy helpers. Copilot unavailable; **Cursor Bugbot** used as stand-in.

### Code changes in this tier (additive on small)
- `power_schedule.py` — Fast/Explore/Exploit/COE-style energy assignment
- `ble_energy.py` — BLE sequence energy + queue ranking + splice helper
- `dictionaries/http_api.dict` — HTTP/API dictionary tokens
- Wire power schedule into `simple_fuzzer2.py` energy assignment / session snapshot
- BLE `Smartlock.py` integration of scheduler, donor splice, interesting-byte mutations

## Reviewer status

| Reviewer | Status | Notes |
|----------|--------|-------|
| **Greptile** | Received | Summary + **2 inline P1s** + outside-diff; confidence **2/5** |
| **GitHub Copilot** | **Not received** | Credits / collaborator 422 |
| **Cursor Bugbot** (stand-in) | Received | 1 high + 4 medium + 1 low |

## What Greptile found

1. **`BLE/Smartlock.py` — Scheduler scores stay empty (P1)** — `assign_energy` / `choose_next` read scheduler state but campaign never calls `record`
2. **`power_schedule.py` — Endpoint statistics conflated (P1)** — fingerprint keyed only on payload
3. **Outside-diff:** BLE splicing unreachable — `mutate_input(seed)` omits donor
4. Mermaid flowchart of missing edges; confidence correctly low (2/5)

## What Cursor Bugbot found

| Severity | Location | Finding |
|----------|----------|---------|
| high | `BLE/Smartlock.py:290-293` | `ble_scheduler.record()` never called → length-only energy |
| medium | `BLE/Smartlock.py:279` | Donor splice never invoked |
| medium | `power_schedule.py:80-93` | Seed stats keyed by payload only |
| medium | `simple_fuzzer2.py` call site | `coverage_gain` always defaults to 0 |
| low | `mutations.py` dict loader | Tokens with `=` and `"` misparsed as AFL `name="value"` |

*(Bugbot also claimed dict tokens unused via `mutate_payload`; disputed — `mutate_payload` → `random_mutation` can still select `dictionary_insert`.)*

## What Copilot found

**Unavailable.**

## Overlap (Greptile ∩ Cursor)

| Finding | Greptile | Cursor |
|---------|----------|--------|
| BLE `record` never called | Yes | Yes |
| BLE donor splice dead | Yes | Yes |
| Schedule payload-only key | Yes | Yes |
| Missing `coverage_gain` at call site | **No** | Yes |
| Dict parse corruption | **No** | Yes |
| Mermaid / confidence score | Yes | No |

**Core integration bugs: full overlap.** Cursor added call-site and parser findings; Greptile added packaging.

## Pitfalls and benefits (this tier)

### Greptile — benefits
- Caught real “feature added but not connected” bugs
- Flowchart + low confidence score make gaps obvious

### Greptile — pitfalls
- Missed `coverage_gain` omission and dict parser edge case
- Outside-diff comments easy to miss in GitHub UI

### Cursor — benefits
- Matched all Greptile integration P1s
- Extra call-site / parser issues

### Cursor — pitfalls
- No confidence score / PR-bot summary for GitHub stakeholders

## Verdict for medium PRs
**Greptile graph review is valuable, but not uniquely so vs Cursor** on this PR—both tools found the same critical unwired-BLE and schedule-keying defects. Pay for Greptile if you need always-on GitHub review without running Cursor; otherwise Cursor already covers the high-signal gaps here.
