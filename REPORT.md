# REPORT.md — PR #2 (Medium tier)

**PR:** https://github.com/T2LIPthedeveloper/AFL-Fuzzer/pull/2  
**Branch:** `develop-2` → `main`  
**Code SHA:** `ce356ed1` · **Δ:** +618 / −21 (includes small)

> Collated analysis: [`GREPTILE_DIFFERENTIAL_CODE_REPORT.md` on develop-3](https://github.com/T2LIPthedeveloper/AFL-Fuzzer/blob/develop-3/GREPTILE_DIFFERENTIAL_CODE_REPORT.md).  
> **“Copilot” = Cursor Bugbot** stand-in.

## What changed (additive)
New: `power_schedule.py`, `ble_energy.py`, `dictionaries/http_api.dict`.  
Wired: schedule blend in `simple_fuzzer2.py`; BLE scheduler + interesting-byte + donor-capable `mutate_input` in `Smartlock.py`; dict file loader in `mutations.py`.

## Greptile (confidence 2/5)
- P1: BLE `record` never called → length-only energy  
- P1: schedule fingerprint payload-only → cross-endpoint conflation  
- Outside-diff: donor splice unreachable  
- Mermaid missing-edge flowchart  

## Copilot (Cursor)
Same three integration issues (high/medium) **plus** `coverage_gain` always 0 at call site; dict `=`/`"` parse corruption (low). Soft FP on “dict unused via mutate_payload.”

## Graph value
**High.** Missing write edge + dead donor are call-graph findings. Copilot found them too without Greptile’s hosted index—so graph *reasoning* mattered; Greptile exclusivity did not.

## Verdict
Greptile packaging (2/5 + diagram) excellent; defect detection largely overlapped with Copilot.
