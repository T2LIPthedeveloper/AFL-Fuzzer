"""
AFL-inspired power schedules for greybox fuzzing.

Assigns mutation energy to queue entries based on coverage yield,
execution cost, seed age, and crash correlation — similar in spirit to
AFL's ``calculate_score`` / power schedules (explore, exploit, COE, etc.).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("PowerSchedule")


class ScheduleMode(str, Enum):
    EXPLORE = "explore"
    EXPLOIT = "exploit"
    COE = "coe"  # cut-off exponential
    FAST = "fast"
    LINEAR = "linear"
    QUAD = "quad"


@dataclass
class SeedStats:
    seed_id: str
    path: str
    method: str
    bytesize: int = 0
    executions: int = 0
    new_coverage_count: int = 0
    total_coverage_gain: float = 0.0
    crashes: int = 0
    last_exec_ms: float = 1.0
    avg_exec_ms: float = 1.0
    discovered_at: float = field(default_factory=time.time)
    depth: int = 0
    handicap: int = 0


def seed_fingerprint(seed: Any) -> str:
    try:
        payload = json.dumps(seed, sort_keys=True, default=str)
    except TypeError:
        payload = repr(seed)
    return hashlib.md5(payload.encode()).hexdigest()


class PowerSchedule:
    """
    Compute AFL-style energy multipliers for seeds in the greybox queue.
    """

    MIN_ENERGY = 1
    MAX_ENERGY = 64
    BASE_ENERGY = 8

    def __init__(self, mode: ScheduleMode = ScheduleMode.FAST):
        self.mode = mode if isinstance(mode, ScheduleMode) else ScheduleMode(mode)
        self.stats: Dict[str, SeedStats] = {}
        self.global_executions = 0
        self.global_coverage_events = 0
        self.start_time = time.time()

    def ensure_stats(
        self,
        seed: Any,
        path: str,
        method: str,
        depth: int = 0,
    ) -> SeedStats:
        sid = seed_fingerprint(seed)
        if sid not in self.stats:
            try:
                size = len(json.dumps(seed, default=str))
            except TypeError:
                size = len(repr(seed))
            self.stats[sid] = SeedStats(
                seed_id=sid,
                path=path,
                method=method,
                bytesize=size,
                depth=depth,
            )
        return self.stats[sid]

    def record_execution(
        self,
        seed: Any,
        path: str,
        method: str,
        *,
        exec_ms: float = 1.0,
        coverage_gain: float = 0.0,
        reveals_bug: bool = False,
        depth: int = 0,
    ) -> SeedStats:
        st = self.ensure_stats(seed, path, method, depth=depth)
        st.executions += 1
        st.last_exec_ms = max(0.1, exec_ms)
        # Exponential moving average for exec time
        alpha = 0.3
        st.avg_exec_ms = (1 - alpha) * st.avg_exec_ms + alpha * st.last_exec_ms
        if coverage_gain > 0:
            st.new_coverage_count += 1
            st.total_coverage_gain += coverage_gain
            self.global_coverage_events += 1
        if reveals_bug:
            st.crashes += 1
        self.global_executions += 1
        return st

    def _mode_factor(self, st: SeedStats) -> float:
        n = max(1, st.executions)
        if self.mode == ScheduleMode.EXPLORE:
            # Prefer under-explored seeds
            return 2.0 / math.sqrt(n)
        if self.mode == ScheduleMode.EXPLOIT:
            # Prefer historically productive seeds
            yield_rate = st.total_coverage_gain / n
            return 0.5 + min(3.0, yield_rate)
        if self.mode == ScheduleMode.COE:
            # Cut-off exponential: ignore seeds that never find coverage after N tries
            if st.executions > 16 and st.new_coverage_count == 0:
                return 0.25
            return 1.0 + math.log2(1 + st.new_coverage_count)
        if self.mode == ScheduleMode.LINEAR:
            return max(0.5, 2.0 - (n * 0.05))
        if self.mode == ScheduleMode.QUAD:
            return max(0.4, 2.0 - ((n * n) * 0.002))
        # FAST (default): mild decay with a coverage boost
        return (1.5 / math.sqrt(n)) * (1.0 + 0.25 * st.new_coverage_count)

    def _speed_factor(self, st: SeedStats) -> float:
        # Faster inputs get more energy (AFL heuristic)
        if st.avg_exec_ms <= 5:
            return 1.4
        if st.avg_exec_ms <= 20:
            return 1.1
        if st.avg_exec_ms <= 100:
            return 1.0
        return 0.7

    def _size_factor(self, st: SeedStats) -> float:
        if st.bytesize < 100:
            return 1.4
        if st.bytesize < 500:
            return 1.15
        if st.bytesize < 2000:
            return 1.0
        return 0.75

    def _age_factor(self, st: SeedStats) -> float:
        age = time.time() - st.discovered_at
        if age < 30:
            return 1.6
        if age < 120:
            return 1.3
        if age < 600:
            return 1.1
        return 1.0

    def _crash_factor(self, st: SeedStats) -> float:
        if st.crashes <= 0:
            return 1.0
        return min(2.0, 1.0 + 0.35 * st.crashes)

    def _depth_factor(self, st: SeedStats) -> float:
        # Deeper mutations (havoc descendants) get a mild handicap decay
        return max(0.5, 1.0 - 0.05 * st.depth - 0.1 * st.handicap)

    def calculate_energy(
        self,
        seed: Any,
        path: str,
        method: str,
        *,
        depth: int = 0,
        extra_multiplier: float = 1.0,
    ) -> int:
        st = self.ensure_stats(seed, path, method, depth=depth)
        raw = (
            self.BASE_ENERGY
            * self._mode_factor(st)
            * self._speed_factor(st)
            * self._size_factor(st)
            * self._age_factor(st)
            * self._crash_factor(st)
            * self._depth_factor(st)
            * max(0.1, extra_multiplier)
        )
        energy = int(round(raw))
        energy = max(self.MIN_ENERGY, min(self.MAX_ENERGY, energy))
        logger.debug(
            "energy=%s mode=%s seed=%s path=%s method=%s execs=%s",
            energy,
            self.mode.value,
            st.seed_id[:8],
            path,
            method,
            st.executions,
        )
        return energy

    def summary(self) -> Dict[str, Any]:
        productive = [
            s for s in self.stats.values() if s.new_coverage_count > 0 or s.crashes > 0
        ]
        return {
            "mode": self.mode.value,
            "tracked_seeds": len(self.stats),
            "global_executions": self.global_executions,
            "global_coverage_events": self.global_coverage_events,
            "productive_seeds": len(productive),
            "uptime_sec": round(time.time() - self.start_time, 2),
            "top_coverage": sorted(
                (
                    {
                        "seed_id": s.seed_id[:12],
                        "path": s.path,
                        "method": s.method,
                        "coverage_gain": s.total_coverage_gain,
                        "crashes": s.crashes,
                        "executions": s.executions,
                    }
                    for s in productive
                ),
                key=lambda x: (x["coverage_gain"], x["crashes"]),
                reverse=True,
            )[:10],
        }


def parse_schedule_mode(value: Optional[str]) -> ScheduleMode:
    if not value:
        return ScheduleMode.FAST
    try:
        return ScheduleMode(value.strip().lower())
    except ValueError:
        logger.warning("Unknown schedule mode %r; defaulting to FAST", value)
        return ScheduleMode.FAST
