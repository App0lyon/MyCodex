import json
import os
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Deque, Dict, List, Sequence, Tuple


def _trim_text(value: str, limit: int) -> str:
    """Return value trimmed to limit characters, keeping the tail if needed."""
    if limit <= 0 or len(value) <= limit:
        return value
    return value[-limit:]


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class MemoryEntry:
    goal: str
    context: str
    constraints: str
    notes: str
    response: str
    history: List[ConversationTurn] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: time.time())
    conversation_id: str = "global"


class MemoryStore:
    """
    Simple short/long term memory to persist past interactions and reuse them
    as contextual hints for the planner/executor pipeline.
    """

    def __init__(
        self,
        path: str = "memory_store.json",
        short_term_limit: int = 5,
        long_term_limit: int = 200,
        max_formatted_chars: int = 2000,
    ) -> None:
        self.path = path
        self.short_term_limit = max(1, short_term_limit)
        self.long_term_limit = max(1, long_term_limit)
        self.max_formatted_chars = max_formatted_chars
        self.default_conversation_id = "global"
        self.short_term_by_session: Dict[str, Deque[MemoryEntry]] = {}
        self.long_term_by_session: Dict[str, List[MemoryEntry]] = {}
        self._load()

    # Public API -----------------------------------------------------------------
    def build_context(
        self,
        goal: str,
        context: str,
        history: Sequence[dict | ConversationTurn] | None = None,
        limit: int = 3,
        conversation_id: str | None = None,
    ) -> Tuple[str, str, List[MemoryEntry]]:
        """
        Return a tuple:
        - context enriched with relevant memory
        - formatted memory text that has been injected
        - list of memory entries used
        """
        session_id = self._resolve_session_id(conversation_id)
        normalized_history = self._normalize_history(history or [])
        entries = self.recall(
            goal=goal,
            context=context,
            history=normalized_history,
            limit=limit,
            conversation_id=session_id,
        )
        memory_text = self.format_entries(entries)

        parts: List[str] = []
        base_context = context.strip()
        if base_context:
            parts.append(base_context)
        if memory_text:
            parts.append("Contexte memoire (discussions passees):\n" + memory_text)

        enriched = _trim_text("\n\n".join(parts).strip(), self.max_formatted_chars)
        return enriched or context, memory_text, entries

    def recall(
        self,
        goal: str,
        context: str,
        history: Sequence[ConversationTurn] | None = None,
        limit: int = 3,
        conversation_id: str | None = None,
    ) -> List[MemoryEntry]:
        """Return relevant memory entries (best-effort keyword match + recents)."""
        session_id = self._resolve_session_id(conversation_id)
        history_text = " ".join(turn.content for turn in (history or []) if isinstance(turn, ConversationTurn))
        query_tokens = self._tokenize(" ".join([goal, context, history_text]))
        scored: List[Tuple[int, float, MemoryEntry]] = []

        for entry in self.long_term_by_session.get(session_id, []):
            haystack = (entry.response or "").lower()
            if not haystack:
                continue
            score = sum(1 for token in query_tokens if token in haystack)
            if score:
                scored.append((score, entry.timestamp, entry))

        scored.sort(key=lambda item: (-item[0], -item[1]))
        selected: List[MemoryEntry] = [item[2] for item in scored[:limit]]

        # Top-up with most recent short term items if not enough matches.
        if len(selected) < limit:
            for entry in reversed(self.short_term_by_session.get(session_id, [])):
                if entry not in selected:
                    selected.append(entry)
                    if len(selected) >= limit:
                        break

        return selected

    def remember_run(
        self,
        goal: str,
        context: str,
        context_used: str,
        constraints: str,
        tasks: List[dict],
        unresolved: List[dict],
        final_critic: dict,
        response: str,
        history: Sequence[dict | ConversationTurn] | None = None,
        conversation_id: str | None = None,
    ) -> None:
        """
        Persist uniquement la reponse finale retournee a l'utilisateur.
        """
        trimmed_response = _trim_text(response or "", 1200)
        if not trimmed_response:
            return
        self.remember(
            goal="",
            context="",
            constraints="",
            notes="",
            response=trimmed_response,
            history=[],
            conversation_id=conversation_id,
        )

    def remember(
        self,
        goal: str,
        context: str,
        constraints: str,
        notes: str,
        response: str,
        history: Sequence[ConversationTurn] | None = None,
        conversation_id: str | None = None,
    ) -> None:
        """Store a new memory entry and persist it to disk."""
        session_id = self._resolve_session_id(conversation_id)
        entry = MemoryEntry(
            goal=goal.strip(),
            context=context.strip(),
            constraints=constraints.strip(),
            notes=notes.strip(),
            response=(response or "").strip(),
            history=list(history or []),
            conversation_id=session_id,
        )

        self._push_entry(entry)
        self._persist()

    def list_entries(self, conversation_id: str | None = None) -> List[MemoryEntry]:
        """Return all entries for a conversation (or all if None)."""
        if conversation_id:
            session_id = self._resolve_session_id(conversation_id)
            return list(self.long_term_by_session.get(session_id, []))
        entries: List[MemoryEntry] = []
        for sess_entries in self.long_term_by_session.values():
            entries.extend(sess_entries)
        return entries

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by its timestamp identifier across sessions. Returns True if removed."""
        removed = False
        for session_id, entries in list(self.long_term_by_session.items()):
            before = len(entries)
            entries[:] = [e for e in entries if str(e.timestamp) != str(entry_id)]
            if len(entries) != before:
                removed = True
                self._sync_session_buffers(session_id)
        if removed:
            self._persist()
        return removed

    def format_entries(self, entries: List[MemoryEntry]) -> str:
        """Return a human-readable memory block to append to prompts."""
        if not entries:
            return ""

        lines: List[str] = []
        for entry in entries:
            if not entry.response:
                continue
            preview = _trim_text(entry.response, 400)
            lines.append(f"- Reponse precedente:\n  {preview}")
        if not lines:
            return ""
        formatted = "\n".join(lines)
        return _trim_text(formatted, self.max_formatted_chars)

    def format_history(self, history: Sequence[ConversationTurn], prefix: str = "") -> str:
        """Compact conversation turns so they can be appended to prompts."""
        if not history:
            return ""
        lines: List[str] = []
        # Keep only the latest turns to avoid bloating prompts.
        for turn in history[-8:]:
            label = "Utilisateur" if (turn.role or "").lower() == "user" else "Assistant"
            lines.append(f"{prefix}{label}: {_trim_text(turn.content, 240)}")
        return "\n".join(lines)

    # Internal helpers ----------------------------------------------------------
    def _tokenize(self, text: str) -> List[str]:
        text = text or ""
        return [token for token in re.split(r"[\s,;:!?.()/\\-]+", text.lower()) if len(token) > 3]

    def _normalize_history(self, history: Sequence[dict | ConversationTurn]) -> List[ConversationTurn]:
        normalized: List[ConversationTurn] = []
        for turn in history:
            if isinstance(turn, ConversationTurn):
                content = turn.content.strip()
                if content:
                    normalized.append(ConversationTurn(role=turn.role or "user", content=_trim_text(content, 1200)))
                continue
            role = None
            content = None
            if isinstance(turn, dict):
                role = turn.get("role", "user")
                content = turn.get("content", "")
            else:
                role = getattr(turn, "role", None) or "user"
                content = getattr(turn, "content", "")
            role = str(role or "user").lower() or "user"
            content = str(content or "").strip()
            if not content:
                continue
            normalized.append(ConversationTurn(role=role, content=_trim_text(content, 1200)))
        # Keep the latest turns to keep prompts compact.
        return normalized[-20:]

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            return

        if not isinstance(data, list):
            return

        for item in data:
            try:
                if not isinstance(item, dict):
                    continue

                history = self._normalize_history(item.get("history", []))
                notes = str(item.get("notes", item.get("summary", "")))
                conversation_id = self._resolve_session_id(item.get("conversation_id"))
                entry = MemoryEntry(
                    goal=str(item.get("goal", "")),
                    context=str(item.get("context", "")),
                    constraints=str(item.get("constraints", "")),
                    notes=notes,
                    response=str(item.get("response", "")),
                    history=history,
                    timestamp=float(item.get("timestamp", time.time())),
                    conversation_id=conversation_id,
                )
                self._push_entry(entry, sync=False)
            except Exception:
                continue

        for session_id in list(self.long_term_by_session.keys()):
            self._sync_session_buffers(session_id)

    def _persist(self) -> None:
        try:
            payload: List[dict] = []
            for entries in self.long_term_by_session.values():
                for entry in entries:
                    payload.append(asdict(entry))
            with open(self.path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
        except Exception:
            # Persistence failure should not block the agent.
            return

    def _resolve_session_id(self, conversation_id: str | None) -> str:
        session_id = str(conversation_id or "").strip()
        return session_id or self.default_conversation_id

    def _push_entry(self, entry: MemoryEntry, sync: bool = True) -> None:
        _, long_term = self._ensure_session(entry.conversation_id)
        long_term.append(entry)
        if sync:
            self._sync_session_buffers(entry.conversation_id)

    def _sync_session_buffers(self, session_id: str) -> None:
        _, long_term = self._ensure_session(session_id)
        # Trim long term memory for this session.
        if len(long_term) > self.long_term_limit:
            long_term[:] = long_term[-self.long_term_limit :]
        # Rebuild short term from the end of the long term buffer.
        recent_slice = list(long_term[-self.short_term_limit :])
        self.short_term_by_session[session_id] = deque(recent_slice, maxlen=self.short_term_limit)

    def _ensure_session(self, session_id: str) -> Tuple[Deque[MemoryEntry], List[MemoryEntry]]:
        if session_id not in self.short_term_by_session:
            self.short_term_by_session[session_id] = deque(maxlen=self.short_term_limit)
        if session_id not in self.long_term_by_session:
            self.long_term_by_session[session_id] = []
        return self.short_term_by_session[session_id], self.long_term_by_session[session_id]
