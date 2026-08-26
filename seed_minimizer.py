"""
Seed minimization and corpus compaction.

Given an interesting seed that unlocked coverage, attempt to shrink it while
preserving the interestingness predicate — analogous to AFL's trim stage but
for structured JSON/API payloads.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("SeedMinimizer")


Predicate = Callable[[Any], bool]


@dataclass
class TrimResult:
    original: Any
    minimized: Any
    original_size: int
    minimized_size: int
    steps: int
    elapsed_ms: float
    success: bool

    @property
    def reduction_ratio(self) -> float:
        if self.original_size <= 0:
            return 0.0
        return 1.0 - (self.minimized_size / float(self.original_size))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_size": self.original_size,
            "minimized_size": self.minimized_size,
            "reduction_ratio": round(self.reduction_ratio, 4),
            "steps": self.steps,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "success": self.success,
            "minimized": self.minimized,
        }


def _size_of(value: Any) -> int:
    try:
        return len(json.dumps(value, sort_keys=True, default=str))
    except TypeError:
        return len(repr(value))


class SeedMinimizer:
    """Trim structured seeds while a caller-provided predicate stays true."""

    def __init__(self, max_steps: int = 80):
        self.max_steps = max_steps
        self.history: List[TrimResult] = []
        self.attempts = 0
        self.successes = 0

    def trim(self, seed: Any, still_interesting: Predicate) -> TrimResult:
        self.attempts += 1
        started = time.time()
        original = copy.deepcopy(seed)
        current = copy.deepcopy(seed)
        if not still_interesting(current):
            result = TrimResult(
                original=original,
                minimized=current,
                original_size=_size_of(original),
                minimized_size=_size_of(current),
                steps=0,
                elapsed_ms=(time.time() - started) * 1000,
                success=False,
            )
            self.history.append(result)
            return result

        steps = 0
        changed = True
        while changed and steps < self.max_steps:
            changed = False
            steps += 1
            if isinstance(current, dict):
                # Drop keys
                for key in list(current.keys()):
                    candidate = copy.deepcopy(current)
                    candidate.pop(key, None)
                    if still_interesting(candidate):
                        current = candidate
                        changed = True
                        break
                if changed:
                    continue
                # Shrink string/list values
                for key, value in list(current.items()):
                    if isinstance(value, str) and len(value) > 1:
                        for new_val in (value[: len(value) // 2], value[:-1], value[1:]):
                            candidate = copy.deepcopy(current)
                            candidate[key] = new_val
                            if still_interesting(candidate):
                                current = candidate
                                changed = True
                                break
                        if changed:
                            break
                    elif isinstance(value, list) and len(value) > 1:
                        mid = len(value) // 2
                        for new_val in (value[:mid], value[mid:]):
                            candidate = copy.deepcopy(current)
                            candidate[key] = new_val
                            if still_interesting(candidate):
                                current = candidate
                                changed = True
                                break
                        if changed:
                            break
                    elif isinstance(value, dict) and value:
                        nested = self.trim(value, lambda v, k=key: still_interesting({**current, k: v}))
                        if nested.success and _size_of(nested.minimized) < _size_of(value):
                            candidate = copy.deepcopy(current)
                            candidate[key] = nested.minimized
                            current = candidate
                            changed = True
                            break
            elif isinstance(current, list) and len(current) > 1:
                mid = len(current) // 2
                for candidate in (current[:mid], current[mid:]):
                    if candidate and still_interesting(candidate):
                        current = candidate
                        changed = True
                        break
            elif isinstance(current, str) and len(current) > 1:
                mid = len(current) // 2
                for candidate in (current[:mid], current[mid:], current[1:], current[:-1]):
                    if still_interesting(candidate):
                        current = candidate
                        changed = True
                        break
            else:
                break

        success = _size_of(current) < _size_of(original)
        if success:
            self.successes += 1
        result = TrimResult(
            original=original,
            minimized=current,
            original_size=_size_of(original),
            minimized_size=_size_of(current),
            steps=steps,
            elapsed_ms=(time.time() - started) * 1000,
            success=success,
        )
        self.history.append(result)
        logger.info(
            "Trim %s -> %s bytes (%.0f%%) in %s steps",
            result.original_size,
            result.minimized_size,
            100 * result.reduction_ratio,
            steps,
        )
        return result

    def compact_corpus(
        self,
        seeds: List[Any],
        still_interesting: Predicate,
    ) -> Tuple[List[Any], Dict[str, Any]]:
        compacted: List[Any] = []
        reductions = []
        for seed in seeds:
            result = self.trim(seed, still_interesting)
            compacted.append(result.minimized if result.success else seed)
            reductions.append(result.reduction_ratio)
        stats = {
            "input_seeds": len(seeds),
            "avg_reduction": round(sum(reductions) / max(1, len(reductions)), 4),
            "successes": self.successes,
            "attempts": self.attempts,
        }
        return compacted, stats

    def summary(self) -> Dict[str, Any]:
        ratios = [h.reduction_ratio for h in self.history if h.success]
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "avg_reduction": round(sum(ratios) / max(1, len(ratios)), 4) if ratios else 0.0,
            "recent": [h.to_dict() for h in self.history[-10:]],
        }
