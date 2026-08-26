"""
Session replay and campaign report generation.

Loads saved SeedQ / crash / coverage artifacts and can re-emit HTTP requests
or produce a self-contained HTML summary for offline analysis.
"""

from __future__ import annotations

import html
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("SessionReplay")


@dataclass
class ReplayEvent:
    path: str
    method: str
    payload: Any
    status_code: Optional[str] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    interesting: bool = False


@dataclass
class SessionReplay:
    session_dir: str
    events: List[ReplayEvent] = field(default_factory=list)
    loaded_seedq: Dict[str, Any] = field(default_factory=dict)
    loaded_failures: Dict[str, Any] = field(default_factory=dict)

    def load(self) -> None:
        seedq_path = os.path.join(self.session_dir, "SeedQ.json")
        fail_path = os.path.join(self.session_dir, "FailureQ.json")
        if os.path.exists(seedq_path):
            with open(seedq_path, "r", encoding="utf-8") as fh:
                self.loaded_seedq = json.load(fh)
        if os.path.exists(fail_path):
            with open(fail_path, "r", encoding="utf-8") as fh:
                self.loaded_failures = json.load(fh)
        logger.info(
            "Loaded session %s (paths=%s failures=%s)",
            self.session_dir,
            len(self.loaded_seedq),
            len(self.loaded_failures),
        )

    def iter_seeds(self) -> Iterable[Tuple[str, str, Any]]:
        for path, meta in self.loaded_seedq.items():
            methods = list((meta.get("methods") or meta.get("methods") or {}).keys())
            if not methods:
                methods = ["GET"]
            seeds = meta.get("seeds") or [{}]
            for method in methods:
                for seed in seeds:
                    body = {} if method in ("GET", "DELETE") else seed
                    yield path, method, body

    def iter_crashes(self) -> Iterable[Dict[str, Any]]:
        for path, methods in self.loaded_failures.items():
            if not isinstance(methods, dict):
                continue
            for method, by_status in methods.items():
                if not isinstance(by_status, dict):
                    continue
                for status, items in by_status.items():
                    for item in items or []:
                        yield {
                            "path": path,
                            "method": method,
                            "status_code": status,
                            "payload": item.get("input") or item.get("payload"),
                            "bug_id": item.get("bug_id"),
                            "error": item.get("error"),
                        }

    def replay(
        self,
        send_fn: Callable[[str, str, Any], Tuple[Any, float, Optional[str]]],
        *,
        limit: int = 100,
        include_crashes: bool = True,
    ) -> List[ReplayEvent]:
        """
        Re-execute seeds using ``send_fn(method, path, payload) -> (response, ms, error)``.
        """
        self.events.clear()
        count = 0
        for path, method, payload in self.iter_seeds():
            if count >= limit:
                break
            started = time.time()
            try:
                response, elapsed_ms, error = send_fn(method, path, payload)
                status = getattr(response, "status_code", None) if response is not None else None
            except Exception as exc:
                response, elapsed_ms, error, status = None, (time.time() - started) * 1000, str(exc), None
            self.events.append(
                ReplayEvent(
                    path=path,
                    method=method,
                    payload=payload,
                    status_code=str(status) if status is not None else None,
                    error=error,
                    elapsed_ms=elapsed_ms,
                )
            )
            count += 1

        if include_crashes:
            for crash in self.iter_crashes():
                if count >= limit:
                    break
                payload = crash.get("payload")
                try:
                    response, elapsed_ms, error = send_fn(crash["method"], crash["path"], payload)
                    status = getattr(response, "status_code", None) if response is not None else crash.get("status_code")
                except Exception as exc:
                    response, elapsed_ms, error, status = None, 0.0, str(exc), crash.get("status_code")
                self.events.append(
                    ReplayEvent(
                        path=crash["path"],
                        method=crash["method"],
                        payload=payload,
                        status_code=str(status) if status is not None else None,
                        error=error or crash.get("error"),
                        elapsed_ms=elapsed_ms,
                    )
                )
                count += 1
        return self.events

    def summary(self) -> Dict[str, Any]:
        statuses: Dict[str, int] = {}
        errors = 0
        for ev in self.events:
            key = ev.status_code or ("ERROR" if ev.error else "NONE")
            statuses[key] = statuses.get(key, 0) + 1
            if ev.error:
                errors += 1
        return {
            "session_dir": self.session_dir,
            "events": len(self.events),
            "status_counts": statuses,
            "errors": errors,
            "seed_paths": len(self.loaded_seedq),
            "failure_paths": len(self.loaded_failures),
        }


def render_campaign_html(
    *,
    title: str,
    power_summary: Optional[Dict[str, Any]] = None,
    corpus_summary: Optional[Dict[str, Any]] = None,
    fuzz_stats: Optional[Dict[str, Any]] = None,
    coverage_summary: Optional[Dict[str, Any]] = None,
    crash_summary: Optional[Dict[str, Any]] = None,
    havoc_stats: Optional[Dict[str, Any]] = None,
    extra_notes: Optional[List[str]] = None,
) -> str:
    """Build a standalone HTML report for a fuzzing campaign."""

    def section(name: str, data: Any) -> str:
        pretty = html.escape(json.dumps(data, indent=2, default=str))
        return f"<section><h2>{html.escape(name)}</h2><pre>{pretty}</pre></section>"

    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        "<style>",
        "body{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;",
        "background:#0f1419;color:#e7ecf1;margin:0;padding:24px;}",
        "h1{font-size:22px;margin:0 0 12px;} h2{font-size:16px;margin:20px 0 8px;color:#9ecbff;}",
        "pre{background:#1b222c;padding:12px;border-radius:8px;overflow:auto;}",
        "header{margin-bottom:18px;padding-bottom:12px;border-bottom:1px solid #2a3441;}",
        "ul{line-height:1.5;} a{color:#9ecbff;}",
        "</style></head><body>",
        f"<header><h1>{html.escape(title)}</h1>",
        f"<div>generated_at={html.escape(time.strftime('%Y-%m-%d %H:%M:%S'))}</div></header>",
    ]
    if extra_notes:
        parts.append("<section><h2>Notes</h2><ul>")
        for note in extra_notes:
            parts.append(f"<li>{html.escape(note)}</li>")
        parts.append("</ul></section>")
    if fuzz_stats is not None:
        parts.append(section("Fuzz Stats", fuzz_stats))
    if power_summary is not None:
        parts.append(section("Power Schedule", power_summary))
    if corpus_summary is not None:
        parts.append(section("Corpus", corpus_summary))
    if coverage_summary is not None:
        parts.append(section("Coverage Bitmap", coverage_summary))
    if crash_summary is not None:
        parts.append(section("Crash Triage", crash_summary))
    if havoc_stats is not None:
        parts.append(section("Havoc Stage", havoc_stats))
    parts.append("</body></html>")
    return "\n".join(parts)


def write_campaign_report(directory: str, **kwargs: Any) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "campaign_report.html")
    html_doc = render_campaign_html(**kwargs)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    logger.info("Campaign HTML report written to %s", path)
    return path
