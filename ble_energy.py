"""
BLE-oriented energy helpers shared by the smart-lock harness.

Mirrors the Django greybox power schedule at a smaller scale: weigh
command sequences by novelty of transition coverage, length, and crash
affinity so BLE campaigns spend more time on promising traces.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("BLEEnergy")


def sequence_id(seq: Sequence[Any]) -> str:
    try:
        blob = json.dumps(seq, sort_keys=True, default=str)
    except TypeError:
        blob = repr(seq)
    return hashlib.sha1(blob.encode()).hexdigest()


@dataclass
class BLESeedScore:
    seq_id: str
    executions: int = 0
    interesting_hits: int = 0
    crash_hits: int = 0
    last_seen: float = field(default_factory=time.time)
    avg_commands: float = 1.0


class BLEEnergyScheduler:
    """Assign mutation energy to BLE command sequences."""

    def __init__(self, base_energy: int = 5, max_energy: int = 24):
        self.base_energy = base_energy
        self.max_energy = max_energy
        self.scores: Dict[str, BLESeedScore] = {}
        self.transition_counts: Dict[Tuple[str, str], int] = {}

    def observe_transition(self, from_state: str, to_state: str) -> int:
        key = (from_state, to_state)
        self.transition_counts[key] = self.transition_counts.get(key, 0) + 1
        return self.transition_counts[key]

    def is_rare_transition(self, from_state: str, to_state: str, threshold: int = 3) -> bool:
        return self.transition_counts.get((from_state, to_state), 0) < threshold

    def record(
        self,
        seq: Sequence[Any],
        *,
        interesting: bool = False,
        crashed: bool = False,
    ) -> BLESeedScore:
        sid = sequence_id(seq)
        score = self.scores.get(sid)
        if score is None:
            score = BLESeedScore(seq_id=sid, avg_commands=max(1.0, float(len(seq))))
            self.scores[sid] = score
        score.executions += 1
        score.last_seen = time.time()
        score.avg_commands = (0.7 * score.avg_commands) + (0.3 * max(1.0, float(len(seq))))
        if interesting:
            score.interesting_hits += 1
        if crashed:
            score.crash_hits += 1
        return score

    def energy_for(self, seq: Sequence[Any]) -> int:
        sid = sequence_id(seq)
        score = self.scores.get(sid)
        length_bonus = min(6, max(0, len(seq) // 2))
        if score is None:
            return min(self.max_energy, self.base_energy + length_bonus)

        novelty = 1.0 + math.log2(1 + score.interesting_hits)
        crash_boost = 1.0 + (0.4 * score.crash_hits)
        # Mild decay so stale sequences do not dominate forever
        age = time.time() - score.last_seen
        age_factor = 1.3 if age < 30 else (1.1 if age < 120 else 1.0)
        explore = 1.4 / math.sqrt(max(1, score.executions))
        raw = self.base_energy * novelty * crash_boost * age_factor * explore + length_bonus
        energy = int(round(raw))
        return max(1, min(self.max_energy, energy))

    def rank_queue(
        self,
        queue: Iterable[Tuple[Sequence[Any], float]],
    ) -> List[Tuple[Sequence[Any], float]]:
        ranked = []
        for seq, weight in queue:
            sid = sequence_id(seq)
            score = self.scores.get(sid)
            boost = 1.0
            if score:
                boost += 0.25 * score.interesting_hits + 0.35 * score.crash_hits
                boost *= 1.2 / math.sqrt(max(1, score.executions))
            ranked.append((seq, max(0.05, weight * boost)))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def summary(self) -> Dict[str, Any]:
        return {
            "tracked_sequences": len(self.scores),
            "transitions": {
                f"{a}->{b}": count for (a, b), count in self.transition_counts.items()
            },
            "top_interesting": sorted(
                (
                    {
                        "seq_id": s.seq_id[:12],
                        "interesting": s.interesting_hits,
                        "crashes": s.crash_hits,
                        "executions": s.executions,
                    }
                    for s in self.scores.values()
                    if s.interesting_hits or s.crash_hits
                ),
                key=lambda x: (x["interesting"], x["crashes"]),
                reverse=True,
            )[:10],
        }


def splice_sequences(a: Sequence[Any], b: Sequence[Any]) -> List[Any]:
    """AFL-inspired splice across two BLE command sequences."""
    if not a:
        return [cmd[:] if isinstance(cmd, list) else cmd for cmd in b]
    if not b:
        return [cmd[:] if isinstance(cmd, list) else cmd for cmd in a]
    cut_a = max(1, len(a) // 2)
    cut_b = max(0, len(b) // 2)
    left = [cmd[:] if isinstance(cmd, list) else cmd for cmd in a[:cut_a]]
    right = [cmd[:] if isinstance(cmd, list) else cmd for cmd in b[cut_b:]]
    return (left + right)[:256]
