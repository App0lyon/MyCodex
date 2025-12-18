import csv
import hashlib
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import tiktoken


@dataclass
class CostLogEntry:
    timestamp: str
    scenario_id: str
    call_id: str
    model: str
    endpoint: str
    prompt_hash: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    status: str
    notes: str = ""


class CostLogger:
    """
    Thread-safe CSV logger for model call costs/tokens.
    """

    HEADERS = [
        "timestamp",
        "scenario_id",
        "call_id",
        "model",
        "endpoint",
        "prompt_hash",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "latency_ms",
        "status",
        "notes",
    ]

    def __init__(self, path: str | Path = "costs.csv") -> None:
        self.path = Path(path)
        self.lock = threading.Lock()
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.path.exists():
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.DictWriter(fp, fieldnames=self.HEADERS)
                writer.writeheader()
        except Exception:
            # Logging failures must never break the agent.
            return

    def hash_prompt(self, prompt_text: str) -> str:
        try:
            return hashlib.sha256((prompt_text or "").encode("utf-8")).hexdigest()
        except Exception:
            return ""

    def count_tokens(self, model: str, text: str) -> int:
        """
        Best-effort token counting using tiktoken; falls back to whitespace split.
        """
        if not text:
            return 0
        try:
            try:
                encoding = tiktoken.encoding_for_model(model)
            except Exception:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback to a simple approximation when encoding is unknown.
            return len(text.split())

    def log(self, entry: CostLogEntry) -> None:
        payload = {
            "timestamp": entry.timestamp,
            "scenario_id": entry.scenario_id,
            "call_id": entry.call_id,
            "model": entry.model,
            "endpoint": entry.endpoint,
            "prompt_hash": entry.prompt_hash,
            "prompt_tokens": entry.prompt_tokens,
            "completion_tokens": entry.completion_tokens,
            "total_tokens": entry.total_tokens,
            "latency_ms": entry.latency_ms,
            "status": entry.status,
            "notes": entry.notes,
        }
        try:
            with self.lock:
                exists = self.path.exists()
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", newline="", encoding="utf-8") as fp:
                    writer = csv.DictWriter(fp, fieldnames=self.HEADERS)
                    if not exists:
                        writer.writeheader()
                    writer.writerow(payload)
        except Exception:
            # CSV write must be non-blocking for the rest of the app.
            return

    def build_entry(
        self,
        scenario_id: str,
        call_id: str,
        model: str,
        endpoint: str,
        prompt_hash: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status: str,
        notes: str = "",
    ) -> CostLogEntry:
        total = max(0, prompt_tokens) + max(0, completion_tokens)
        return CostLogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenario_id=scenario_id or "unknown",
            call_id=call_id,
            model=model,
            endpoint=endpoint,
            prompt_hash=prompt_hash,
            prompt_tokens=max(0, prompt_tokens),
            completion_tokens=max(0, completion_tokens),
            total_tokens=total,
            latency_ms=max(0, latency_ms),
            status=status or "unknown",
            notes=notes,
        )

    def log_failure(
        self,
        scenario_id: str,
        call_id: str,
        model: str,
        endpoint: str,
        prompt_hash: str,
        prompt_tokens: int,
        latency_ms: int,
        error: Exception,
        notes: str = "",
    ) -> None:
        status = f"error:{error.__class__.__name__}"
        merged_notes = f"{notes} | {error}".strip(" |")
        entry = self.build_entry(
            scenario_id=scenario_id,
            call_id=call_id,
            model=model,
            endpoint=endpoint,
            prompt_hash=prompt_hash,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            status=status,
            notes=merged_notes,
        )
        self.log(entry)

    def log_success(
        self,
        scenario_id: str,
        call_id: str,
        model: str,
        endpoint: str,
        prompt_hash: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status: str = "success",
        notes: str = "",
    ) -> None:
        entry = self.build_entry(
            scenario_id=scenario_id,
            call_id=call_id,
            model=model,
            endpoint=endpoint,
            prompt_hash=prompt_hash,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status or "success",
            notes=notes,
        )
        self.log(entry)


def utc_ms() -> int:
    return int(time.time() * 1000)
