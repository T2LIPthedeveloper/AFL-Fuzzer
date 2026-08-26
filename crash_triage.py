"""
Crash triage, deduplication, and minimization helpers.

Groups crashing HTTP / BLE inputs by normalized signatures (status,
exception class, stack-ish tokens, endpoint) and can delta-minimize
JSON payloads while preserving the crash signature — an AFL-inspired
workflow adapted to API fuzzing.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("CrashTriage")

EXCEPTION_RE = re.compile(
    r"(?P<exc>[A-Za-z_][\w.]*(?:Error|Exception|Fault|Panic|Timeout))",
)
FRAME_RE = re.compile(r'File "([^"]+)", line (\d+), in ([^\s]+)')


def _canonicalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Drop volatile tokens (addresses, timestamps, UUIDs)
    cleaned = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", text)
    cleaned = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        "UUID",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "TIMESTAMP", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:4000]


def extract_exception_name(text: Optional[str]) -> str:
    if not text:
        return "Unknown"
    match = EXCEPTION_RE.search(text)
    return match.group("exc") if match else "Unknown"


def extract_frames(text: Optional[str], limit: int = 5) -> List[str]:
    if not text:
        return []
    frames = [f"{m.group(1)}:{m.group(2)}:{m.group(3)}" for m in FRAME_RE.finditer(text)]
    return frames[:limit]


@dataclass
class CrashCase:
    crash_id: str
    signature: str
    path: str
    method: str
    status_code: str
    payload: Any
    response_excerpt: str = ""
    error_excerpt: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    count: int = 1
    minimized_payload: Any = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crash_id": self.crash_id,
            "signature": self.signature,
            "path": self.path,
            "method": self.method,
            "status_code": self.status_code,
            "payload": self.payload,
            "minimized_payload": self.minimized_payload,
            "response_excerpt": self.response_excerpt[:1000],
            "error_excerpt": self.error_excerpt[:1000],
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "count": self.count,
            "tags": self.tags,
        }


class CrashTriage:
    """Deduplicate and optionally minimize crashing inputs."""

    def __init__(self):
        self.cases: Dict[str, CrashCase] = {}
        self.signature_index: Dict[str, str] = {}
        self.total_crashes = 0

    def build_signature(
        self,
        path: str,
        method: str,
        status_code: Any,
        response_text: Optional[str] = None,
        error_text: Optional[str] = None,
    ) -> str:
        exc = extract_exception_name(error_text or response_text)
        frames = extract_frames(error_text or response_text)
        status = str(status_code)
        body_hash = hashlib.md5(
            _canonicalize_text(response_text or error_text).encode()
        ).hexdigest()[:10]
        frame_part = ";".join(frames) if frames else "noframe"
        raw = f"{method}|{path}|{status}|{exc}|{frame_part}|{body_hash}"
        return hashlib.sha1(raw.encode()).hexdigest()

    def record(
        self,
        path: str,
        method: str,
        status_code: Any,
        payload: Any,
        *,
        response_text: Optional[str] = None,
        error_text: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> Tuple[bool, CrashCase]:
        """
        Record a crash. Returns ``(is_new, case)``.
        """
        self.total_crashes += 1
        signature = self.build_signature(path, method, status_code, response_text, error_text)
        if signature in self.signature_index:
            case = self.cases[self.signature_index[signature]]
            case.count += 1
            case.last_seen = time.time()
            return False, case

        crash_id = f"crash-{len(self.cases) + 1:04d}"
        case = CrashCase(
            crash_id=crash_id,
            signature=signature,
            path=path,
            method=method,
            status_code=str(status_code),
            payload=copy.deepcopy(payload),
            response_excerpt=_canonicalize_text(response_text)[:1000],
            error_excerpt=_canonicalize_text(error_text)[:1000],
            tags=list(tags or []),
        )
        # Auto-tag common classes
        if str(status_code) == "CRASH" or "Connection" in (error_text or ""):
            case.tags.append("server-down")
        if extract_exception_name(error_text or response_text) != "Unknown":
            case.tags.append("exception")
        try:
            code_int = int(status_code)
            if code_int >= 500:
                case.tags.append("http-5xx")
        except (TypeError, ValueError):
            pass

        self.cases[crash_id] = case
        self.signature_index[signature] = crash_id
        logger.warning("New unique crash %s sig=%s %s %s", crash_id, signature[:12], method, path)
        return True, case

    def minimize_payload(
        self,
        case: CrashCase,
        still_crashes: Callable[[Any], bool],
        max_steps: int = 64,
    ) -> Any:
        """
        Delta-debug style minimization for dict/list/string payloads.

        ``still_crashes(candidate)`` must return True when the candidate
        reproduces the crash signature / failure.
        """
        current = copy.deepcopy(case.payload)
        if not still_crashes(current):
            logger.info("Original payload no longer reproduces %s; skipping minimize", case.crash_id)
            return current

        steps = 0
        changed = True
        while changed and steps < max_steps:
            changed = False
            steps += 1
            if isinstance(current, dict) and current:
                for key in list(current.keys()):
                    candidate = copy.deepcopy(current)
                    candidate.pop(key, None)
                    if still_crashes(candidate):
                        current = candidate
                        changed = True
                        break
                if changed:
                    continue
                for key, value in list(current.items()):
                    if isinstance(value, str) and len(value) > 1:
                        for cut in (len(value) // 2, max(1, len(value) - 1)):
                            candidate = copy.deepcopy(current)
                            candidate[key] = value[:cut]
                            if still_crashes(candidate):
                                current = candidate
                                changed = True
                                break
                        if changed:
                            break
                    elif isinstance(value, int):
                        for trial in (0, 1, -1, value // 2):
                            if trial == value:
                                continue
                            candidate = copy.deepcopy(current)
                            candidate[key] = trial
                            if still_crashes(candidate):
                                current = candidate
                                changed = True
                                break
                        if changed:
                            break
            elif isinstance(current, list) and len(current) > 1:
                mid = len(current) // 2
                for candidate in (current[:mid], current[mid:]):
                    if candidate and still_crashes(candidate):
                        current = candidate
                        changed = True
                        break
            elif isinstance(current, str) and len(current) > 1:
                mid = len(current) // 2
                for candidate in (current[:mid], current[mid:]):
                    if candidate and still_crashes(candidate):
                        current = candidate
                        changed = True
                        break
            else:
                break

        case.minimized_payload = copy.deepcopy(current)
        logger.info(
            "Minimized %s in %s steps (%s -> %s bytes approx)",
            case.crash_id,
            steps,
            len(json.dumps(case.payload, default=str)),
            len(json.dumps(current, default=str)),
        )
        return current

    def summary(self) -> Dict[str, Any]:
        by_tag: Dict[str, int] = {}
        for case in self.cases.values():
            for tag in case.tags or ["untagged"]:
                by_tag[tag] = by_tag.get(tag, 0) + 1
        return {
            "unique_crashes": len(self.cases),
            "total_crashes": self.total_crashes,
            "by_tag": by_tag,
            "cases": [c.to_dict() for c in sorted(self.cases.values(), key=lambda x: -x.count)],
        }

    def save(self, directory: str, basename: str = "crash_triage") -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{basename}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.summary(), fh, indent=2, default=str)
        # Also write individual crashing payloads for replay
        crash_dir = os.path.join(directory, "crashes")
        os.makedirs(crash_dir, exist_ok=True)
        for case in self.cases.values():
            with open(os.path.join(crash_dir, f"{case.crash_id}.json"), "w", encoding="utf-8") as fh:
                json.dump(case.to_dict(), fh, indent=2, default=str)
        logger.info("Crash triage saved (%s unique) -> %s", len(self.cases), path)
        return path


def prioritize_crashes(cases: Iterable[CrashCase]) -> List[CrashCase]:
    """Rank crashes for human review: rare signatures and 5xx/server-down first."""
    def score(c: CrashCase) -> Tuple[int, int, float]:
        severity = 0
        if "server-down" in c.tags:
            severity += 5
        if "http-5xx" in c.tags:
            severity += 3
        if "exception" in c.tags:
            severity += 2
        return (severity, c.count, -c.first_seen)

    return sorted(cases, key=score, reverse=True)
