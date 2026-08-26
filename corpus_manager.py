"""
Corpus / seed-queue management for the Django greybox fuzzer.

Provides AFL-like queue operations: enqueue interesting inputs, favor
rare path/method pairs, persist corpus snapshots, and select the next
seed with weighted sampling.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("CorpusManager")


@dataclass
class CorpusEntry:
    path: str
    method: str
    seed: Any
    weight: float = 1.0
    favored: bool = False
    depth: int = 0
    found_at: float = field(default_factory=time.time)
    coverage_score: float = 0.0
    crash_count: int = 0
    exec_count: int = 0
    parent_id: Optional[str] = None

    @property
    def entry_id(self) -> str:
        blob = json.dumps(
            {"path": self.path, "method": self.method, "seed": self.seed},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha1(blob.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "seed": self.seed,
            "weight": self.weight,
            "favored": self.favored,
            "depth": self.depth,
            "found_at": self.found_at,
            "coverage_score": self.coverage_score,
            "crash_count": self.crash_count,
            "exec_count": self.exec_count,
            "parent_id": self.parent_id,
            "entry_id": self.entry_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorpusEntry":
        return cls(
            path=data["path"],
            method=data["method"],
            seed=data["seed"],
            weight=float(data.get("weight", 1.0)),
            favored=bool(data.get("favored", False)),
            depth=int(data.get("depth", 0)),
            found_at=float(data.get("found_at", time.time())),
            coverage_score=float(data.get("coverage_score", 0.0)),
            crash_count=int(data.get("crash_count", 0)),
            exec_count=int(data.get("exec_count", 0)),
            parent_id=data.get("parent_id"),
        )


class CorpusManager:
    """Maintain a deduplicated, weighted seed corpus."""

    def __init__(self, max_size: int = 2000):
        self.max_size = max_size
        self.entries: Dict[str, CorpusEntry] = {}
        self.path_method_counts: Dict[str, int] = {}
        self.rejected_duplicates = 0
        self.enqueued = 0

    def __len__(self) -> int:
        return len(self.entries)

    def _pm_key(self, path: str, method: str) -> str:
        return f"{method}:{path}"

    def ingest_seedq(self, seedq: Dict[str, Any]) -> int:
        """
        Import legacy SeedQ structure:
        { path: { methods: {METHOD: True}, seeds: [payload, ...] } }
        """
        added = 0
        for path, meta in (seedq or {}).items():
            methods = list((meta.get("methods") or {}).keys()) or ["GET"]
            seeds = meta.get("seeds") or [{}]
            for method in methods:
                for seed in seeds:
                    # GET/DELETE typically have empty body
                    body = {} if method in ("GET", "DELETE") else seed
                    if self.add(path, method, body, weight=1.0, depth=0):
                        added += 1
        logger.info("Ingested %s seeds from SeedQ (corpus size=%s)", added, len(self))
        return added

    def add(
        self,
        path: str,
        method: str,
        seed: Any,
        *,
        weight: float = 1.0,
        depth: int = 0,
        coverage_score: float = 0.0,
        parent_id: Optional[str] = None,
        favored: bool = False,
    ) -> bool:
        entry = CorpusEntry(
            path=path,
            method=method,
            seed=seed,
            weight=weight,
            depth=depth,
            coverage_score=coverage_score,
            parent_id=parent_id,
            favored=favored,
        )
        eid = entry.entry_id
        if eid in self.entries:
            existing = self.entries[eid]
            existing.weight = max(existing.weight, weight)
            existing.coverage_score = max(existing.coverage_score, coverage_score)
            if favored:
                existing.favored = True
            self.rejected_duplicates += 1
            return False

        if len(self.entries) >= self.max_size:
            self._evict_lowest()

        self.entries[eid] = entry
        pm = self._pm_key(path, method)
        self.path_method_counts[pm] = self.path_method_counts.get(pm, 0) + 1
        self.enqueued += 1
        return True

    def _evict_lowest(self) -> None:
        if not self.entries:
            return
        # Prefer evicting non-favored, low-weight, high-depth entries
        ranked = sorted(
            self.entries.values(),
            key=lambda e: (
                e.favored,
                e.coverage_score,
                e.weight,
                -e.depth,
                -e.exec_count,
            ),
        )
        victim = ranked[0]
        del self.entries[victim.entry_id]
        pm = self._pm_key(victim.path, victim.method)
        self.path_method_counts[pm] = max(0, self.path_method_counts.get(pm, 1) - 1)
        logger.debug("Evicted corpus entry %s", victim.entry_id[:10])

    def mark_result(
        self,
        entry_id: str,
        *,
        coverage_gain: float = 0.0,
        reveals_bug: bool = False,
    ) -> None:
        entry = self.entries.get(entry_id)
        if not entry:
            return
        entry.exec_count += 1
        if coverage_gain > 0:
            entry.coverage_score += coverage_gain
            entry.weight = min(8.0, entry.weight + 0.35 * coverage_gain)
            entry.favored = True
        else:
            entry.weight = max(0.2, entry.weight * 0.97)
        if reveals_bug:
            entry.crash_count += 1
            entry.weight = min(10.0, entry.weight + 0.75)
            entry.favored = True

    def choose_next(self, favor_rare_paths: bool = True) -> Optional[CorpusEntry]:
        if not self.entries:
            return None

        candidates = list(self.entries.values())
        weights: List[float] = []
        for e in candidates:
            w = max(0.05, e.weight)
            if e.favored:
                w *= 1.5
            if favor_rare_paths:
                pm = self._pm_key(e.path, e.method)
                count = self.path_method_counts.get(pm, 1)
                # Inverse frequency boost
                w *= 1.0 + (1.0 / max(1, count))
            # Mild novelty preference for younger seeds
            age = time.time() - e.found_at
            if age < 60:
                w *= 1.25
            weights.append(w)

        total = sum(weights)
        if total <= 0:
            return random.choice(candidates)

        pick = random.uniform(0, total)
        upto = 0.0
        for entry, w in zip(candidates, weights):
            upto += w
            if upto >= pick:
                return entry
        return candidates[-1]

    def favored_entries(self) -> List[CorpusEntry]:
        return [e for e in self.entries.values() if e.favored]

    def export_seedq(self) -> Dict[str, Any]:
        seedq: Dict[str, Any] = {}
        for e in self.entries.values():
            bucket = seedq.setdefault(e.path, {"methods": {}, "seeds": []})
            bucket["methods"][e.method] = True
            if e.method not in ("GET", "DELETE") and e.seed not in bucket["seeds"]:
                bucket["seeds"].append(e.seed)
            elif e.method in ("GET", "DELETE") and not bucket["seeds"]:
                bucket["seeds"].append({})
        return seedq

    def save(self, directory: str, filename: str = "corpus.json") -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        payload = {
            "saved_at": time.time(),
            "max_size": self.max_size,
            "enqueued": self.enqueued,
            "rejected_duplicates": self.rejected_duplicates,
            "entries": [e.to_dict() for e in self.entries.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        logger.info("Corpus saved (%s entries) -> %s", len(self), path)
        return path

    def load(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.entries.clear()
        self.path_method_counts.clear()
        loaded = 0
        for raw in payload.get("entries", []):
            entry = CorpusEntry.from_dict(raw)
            self.entries[entry.entry_id] = entry
            pm = self._pm_key(entry.path, entry.method)
            self.path_method_counts[pm] = self.path_method_counts.get(pm, 0) + 1
            loaded += 1
        self.max_size = int(payload.get("max_size", self.max_size))
        self.enqueued = int(payload.get("enqueued", loaded))
        self.rejected_duplicates = int(payload.get("rejected_duplicates", 0))
        logger.info("Loaded %s corpus entries from %s", loaded, path)
        return loaded

    def summary(self) -> Dict[str, Any]:
        return {
            "size": len(self),
            "favored": len(self.favored_entries()),
            "enqueued": self.enqueued,
            "rejected_duplicates": self.rejected_duplicates,
            "path_methods": dict(self.path_method_counts),
            "avg_weight": (
                round(sum(e.weight for e in self.entries.values()) / len(self.entries), 3)
                if self.entries
                else 0.0
            ),
        }


def merge_interesting(
    manager: CorpusManager,
    path: str,
    method: str,
    seeds: Iterable[Any],
    *,
    parent_id: Optional[str] = None,
    depth: int = 1,
) -> Tuple[int, int]:
    """Convenience helper returning (added, skipped)."""
    added = skipped = 0
    for seed in seeds:
        if manager.add(
            path,
            method,
            seed,
            weight=1.4,
            depth=depth,
            coverage_score=1.0,
            parent_id=parent_id,
            favored=True,
        ):
            added += 1
        else:
            skipped += 1
    return added, skipped
