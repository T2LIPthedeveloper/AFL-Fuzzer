"""
Runtime fuzzing statistics and lightweight session reports.

Aggregates coverage events, crashes, throughput, and mutation telemetry
so operators can compare campaigns without digging through raw logs.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("FuzzStats")


@dataclass
class CrashRecord:
    bug_id: str
    path: str
    method: str
    status_code: str
    first_seen: float
    count: int = 1
    sample_payload: Any = None


@dataclass
class FuzzStatsCollector:
    campaign_name: str = "django-greybox"
    started_at: float = field(default_factory=time.time)
    iterations: int = 0
    interesting: int = 0
    crashes: int = 0
    timeouts: int = 0
    http_5xx: int = 0
    bytes_sent: int = 0
    unique_paths: Counter = field(default_factory=Counter)
    status_codes: Counter = field(default_factory=Counter)
    mutation_hits: Counter = field(default_factory=Counter)
    crash_records: Dict[str, CrashRecord] = field(default_factory=dict)
    coverage_timeline: List[Dict[str, Any]] = field(default_factory=list)
    throughput_window: List[float] = field(default_factory=list)

    def note_iteration(
        self,
        *,
        path: str,
        method: str,
        status_code: Any = None,
        interesting: bool = False,
        reveals_bug: bool = False,
        timeout: bool = False,
        payload_bytes: int = 0,
        coverage_gain: float = 0.0,
        bug_id: Optional[str] = None,
        sample_payload: Any = None,
    ) -> None:
        self.iterations += 1
        self.unique_paths[f"{method}:{path}"] += 1
        self.bytes_sent += max(0, payload_bytes)
        self.throughput_window.append(time.time())
        # Keep a rolling ~60s window
        cutoff = time.time() - 60
        self.throughput_window = [t for t in self.throughput_window if t >= cutoff]

        if status_code is not None:
            self.status_codes[str(status_code)] += 1
            try:
                code_int = int(status_code)
                if code_int >= 500:
                    self.http_5xx += 1
            except (TypeError, ValueError):
                pass

        if interesting or coverage_gain > 0:
            self.interesting += 1
            self.coverage_timeline.append(
                {
                    "t": time.time() - self.started_at,
                    "iteration": self.iterations,
                    "path": path,
                    "method": method,
                    "coverage_gain": coverage_gain,
                }
            )

        if timeout:
            self.timeouts += 1

        if reveals_bug and bug_id:
            self.crashes += 1
            if bug_id in self.crash_records:
                self.crash_records[bug_id].count += 1
            else:
                self.crash_records[bug_id] = CrashRecord(
                    bug_id=bug_id,
                    path=path,
                    method=method,
                    status_code=str(status_code),
                    first_seen=time.time(),
                    sample_payload=sample_payload,
                )

    def note_mutations(self, hits: Optional[Dict[str, int]]) -> None:
        if not hits:
            return
        for name, count in hits.items():
            self.mutation_hits[name] += int(count)

    def execs_per_sec(self) -> float:
        elapsed = max(0.001, time.time() - self.started_at)
        return self.iterations / elapsed

    def recent_execs_per_sec(self) -> float:
        return float(len(self.throughput_window)) / 60.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "campaign": self.campaign_name,
            "uptime_sec": round(time.time() - self.started_at, 2),
            "iterations": self.iterations,
            "interesting": self.interesting,
            "crashes_unique": len(self.crash_records),
            "crashes_total": self.crashes,
            "timeouts": self.timeouts,
            "http_5xx": self.http_5xx,
            "bytes_sent": self.bytes_sent,
            "execs_per_sec": round(self.execs_per_sec(), 3),
            "recent_execs_per_sec": round(self.recent_execs_per_sec(), 3),
            "top_paths": self.unique_paths.most_common(10),
            "status_codes": dict(self.status_codes),
            "mutation_hits": dict(self.mutation_hits),
            "coverage_events": len(self.coverage_timeline),
            "crashes": [
                {
                    "bug_id": c.bug_id,
                    "path": c.path,
                    "method": c.method,
                    "status_code": c.status_code,
                    "count": c.count,
                    "first_seen_age": round(time.time() - c.first_seen, 2),
                }
                for c in sorted(
                    self.crash_records.values(),
                    key=lambda x: x.count,
                    reverse=True,
                )[:25]
            ],
        }

    def render_text(self) -> str:
        snap = self.snapshot()
        lines = [
            f"=== Fuzz Stats: {snap['campaign']} ===",
            f"uptime: {snap['uptime_sec']}s | iters: {snap['iterations']} | "
            f"exec/s: {snap['execs_per_sec']} (recent {snap['recent_execs_per_sec']})",
            f"interesting: {snap['interesting']} | unique crashes: {snap['crashes_unique']} "
            f"(total {snap['crashes_total']}) | timeouts: {snap['timeouts']} | 5xx: {snap['http_5xx']}",
            f"bytes sent: {snap['bytes_sent']}",
            "top paths:",
        ]
        for path, count in snap["top_paths"]:
            lines.append(f"  - {path}: {count}")
        if snap["mutation_hits"]:
            lines.append("mutation hits:")
            for name, count in sorted(
                snap["mutation_hits"].items(), key=lambda x: x[1], reverse=True
            )[:12]:
                lines.append(f"  - {name}: {count}")
        if snap["crashes"]:
            lines.append("crashes:")
            for c in snap["crashes"][:10]:
                lines.append(
                    f"  - {c['bug_id']} {c['method']} {c['path']} "
                    f"status={c['status_code']} count={c['count']}"
                )
        return "\n".join(lines)

    def save(self, directory: str, basename: str = "fuzz_stats") -> Dict[str, str]:
        os.makedirs(directory, exist_ok=True)
        json_path = os.path.join(directory, f"{basename}.json")
        txt_path = os.path.join(directory, f"{basename}.txt")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2, default=str)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.render_text())
            f.write("\n")
        logger.info("Fuzz stats written to %s and %s", json_path, txt_path)
        return {"json": json_path, "txt": txt_path}


def merge_counters(*counters: Counter) -> Counter:
    out: Counter = Counter()
    for c in counters:
        out.update(c)
    return out


def group_crashes_by_endpoint(collector: FuzzStatsCollector) -> Dict[str, int]:
    grouped: Dict[str, int] = defaultdict(int)
    for crash in collector.crash_records.values():
        grouped[f"{crash.method}:{crash.path}"] += crash.count
    return dict(grouped)
