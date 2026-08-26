"""
Edge / coverage bitmap utilities for greybox fuzzing.

Emulates AFL's shared-memory coverage map at the HTTP layer: each
observed (endpoint, method, status, response-shape) tuple hashes into a
bucket. New or rare buckets mark inputs as interesting and drive
favoring / power-schedule boosts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger("CoverageBitmap")

DEFAULT_MAP_SIZE = 1 << 16  # 64k buckets, AFL-like


def _stable_hash(parts: Sequence[Any]) -> int:
    blob = "|".join("" if p is None else str(p) for p in parts)
    digest = hashlib.md5(blob.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16)


def classify_status(status_code: Any) -> str:
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        return "ERR"
    if code < 100:
        return "ERR"
    if code < 200:
        return "1xx"
    if code < 300:
        return "2xx"
    if code < 400:
        return "3xx"
    if code < 500:
        return "4xx"
    return "5xx"


def response_shape(payload: Any, max_keys: int = 8) -> str:
    """Coarse structural fingerprint of a JSON-ish response body."""
    if payload is None:
        return "none"
    if isinstance(payload, (bytes, bytearray)):
        return f"bytes:{len(payload)}"
    if isinstance(payload, str):
        return f"str:{min(len(payload), 2048) // 64}"
    if isinstance(payload, list):
        return f"list:{min(len(payload), 64)}"
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())[:max_keys]
        return "obj:" + ",".join(keys)
    return type(payload).__name__


@dataclass
class CoverageEvent:
    path: str
    method: str
    status_class: str
    shape: str
    bucket: int
    first_seen: float
    hit_count: int = 1
    last_seed_id: Optional[str] = None


@dataclass
class CoverageBitmap:
    map_size: int = DEFAULT_MAP_SIZE
    virgin_bits: bytearray = field(default_factory=lambda: bytearray(DEFAULT_MAP_SIZE))
    hit_counts: bytearray = field(default_factory=lambda: bytearray(DEFAULT_MAP_SIZE))
    events: Dict[int, CoverageEvent] = field(default_factory=dict)
    total_updates: int = 0
    new_edge_events: int = 0
    started_at: float = field(default_factory=time.time)
    path_method_edges: Counter = field(default_factory=Counter)

    def __post_init__(self) -> None:
        if len(self.virgin_bits) != self.map_size:
            self.virgin_bits = bytearray([0xFF] * self.map_size)
        if len(self.hit_counts) != self.map_size:
            self.hit_counts = bytearray(self.map_size)
        if not any(self.virgin_bits):
            # Fresh map: all bits virgin
            self.virgin_bits = bytearray([0xFF] * self.map_size)

    def bucket_for(
        self,
        path: str,
        method: str,
        status_code: Any = None,
        body: Any = None,
        extra: Optional[Sequence[Any]] = None,
    ) -> int:
        parts: List[Any] = [method.upper(), path, classify_status(status_code), response_shape(body)]
        if extra:
            parts.extend(extra)
        return _stable_hash(parts) % self.map_size

    def observe(
        self,
        path: str,
        method: str,
        status_code: Any = None,
        body: Any = None,
        *,
        seed_id: Optional[str] = None,
        extra: Optional[Sequence[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record an execution trace feature.

        Returns a dict with ``is_new``, ``bucket``, ``hit_count``, and
        ``rarity`` (higher = rarer edge).
        """
        bucket = self.bucket_for(path, method, status_code, body, extra=extra)
        self.total_updates += 1
        prev = self.hit_counts[bucket]
        # Saturating 8-bit counter with AFL-style bucketization feel
        nxt = 255 if prev >= 255 else prev + 1
        self.hit_counts[bucket] = nxt

        is_new = (self.virgin_bits[bucket] & 0x01) != 0
        if is_new:
            self.virgin_bits[bucket] = 0
            self.new_edge_events += 1
            self.events[bucket] = CoverageEvent(
                path=path,
                method=method,
                status_class=classify_status(status_code),
                shape=response_shape(body),
                bucket=bucket,
                first_seen=time.time(),
                hit_count=1,
                last_seed_id=seed_id,
            )
        else:
            ev = self.events.get(bucket)
            if ev:
                ev.hit_count += 1
                ev.last_seed_id = seed_id

        self.path_method_edges[f"{method}:{path}"] += 1
        rarity = 1.0 / math.sqrt(max(1, nxt))
        return {
            "is_new": is_new,
            "bucket": bucket,
            "hit_count": nxt,
            "rarity": rarity,
            "status_class": classify_status(status_code),
        }

    def coverage_ratio(self) -> float:
        filled = self.map_size - sum(1 for b in self.virgin_bits if b)
        return filled / float(self.map_size)

    def interesting_score(self, observation: Dict[str, Any]) -> float:
        score = 0.0
        if observation.get("is_new"):
            score += 3.0
        score += float(observation.get("rarity", 0.0))
        if observation.get("status_class") == "5xx":
            score += 1.5
        return score

    def top_edges(self, limit: int = 20) -> List[Dict[str, Any]]:
        ranked = sorted(self.events.values(), key=lambda e: e.hit_count)
        out = []
        for ev in ranked[:limit]:
            out.append(
                {
                    "bucket": ev.bucket,
                    "path": ev.path,
                    "method": ev.method,
                    "status_class": ev.status_class,
                    "shape": ev.shape,
                    "hit_count": ev.hit_count,
                    "age_sec": round(time.time() - ev.first_seen, 2),
                }
            )
        return out

    def summary(self) -> Dict[str, Any]:
        filled = self.map_size - sum(1 for b in self.virgin_bits if b)
        return {
            "map_size": self.map_size,
            "filled_buckets": filled,
            "coverage_ratio": round(self.coverage_ratio(), 6),
            "total_updates": self.total_updates,
            "new_edge_events": self.new_edge_events,
            "unique_events": len(self.events),
            "uptime_sec": round(time.time() - self.started_at, 2),
            "top_paths": self.path_method_edges.most_common(10),
            "rarest_edges": self.top_edges(10),
        }

    def save(self, directory: str, basename: str = "coverage_bitmap") -> Dict[str, str]:
        os.makedirs(directory, exist_ok=True)
        meta_path = os.path.join(directory, f"{basename}.json")
        raw_path = os.path.join(directory, f"{basename}.bin")
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(self.summary(), fh, indent=2)
        with open(raw_path, "wb") as fh:
            fh.write(bytes(self.hit_counts))
        logger.info("Coverage bitmap saved (%s buckets filled)", self.summary()["filled_buckets"])
        return {"json": meta_path, "bin": raw_path}

    def load_hit_counts(self, path: str) -> None:
        with open(path, "rb") as fh:
            data = fh.read()
        if len(data) != self.map_size:
            raise ValueError(f"bitmap size mismatch: got {len(data)}, expected {self.map_size}")
        self.hit_counts = bytearray(data)
        for i, val in enumerate(self.hit_counts):
            if val:
                self.virgin_bits[i] = 0


def merge_bitmaps(bitmaps: Iterable[CoverageBitmap]) -> CoverageBitmap:
    bitmaps = list(bitmaps)
    if not bitmaps:
        return CoverageBitmap()
    size = bitmaps[0].map_size
    merged = CoverageBitmap(map_size=size)
    for bm in bitmaps:
        if bm.map_size != size:
            raise ValueError("cannot merge bitmaps of different sizes")
        for i, val in enumerate(bm.hit_counts):
            if val:
                merged.hit_counts[i] = min(255, merged.hit_counts[i] + val)
                merged.virgin_bits[i] = 0
        merged.total_updates += bm.total_updates
        merged.new_edge_events += bm.new_edge_events
        merged.events.update(bm.events)
        merged.path_method_edges.update(bm.path_method_edges)
    return merged


def edge_key(path: str, method: str, status_code: Any = None, body: Any = None) -> str:
    return f"{method}:{path}:{classify_status(status_code)}:{response_shape(body)}"
