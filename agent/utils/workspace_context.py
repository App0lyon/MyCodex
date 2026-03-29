import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List


class WorkspaceContextBuilder:
    EXCLUDED_DIRS = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".next",
        ".idea",
        ".vscode",
        "coverage",
    }
    BINARY_SUFFIXES = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".7z",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".mov",
        ".avi",
        ".class",
        ".jar",
        ".pyc",
        ".pyo",
        ".lock",
    }
    STOPWORDS = {
        "avec",
        "dans",
        "pour",
        "this",
        "that",
        "from",
        "have",
        "your",
        "will",
        "just",
        "then",
        "into",
        "make",
        "real",
        "like",
        "agent",
        "code",
        "file",
        "files",
        "context",
        "search",
        "workspace",
        "goal",
        "need",
        "want",
        "user",
        "task",
        "project",
        "version",
        "using",
        "used",
        "when",
        "what",
        "where",
    }

    def __init__(self, workspace_root: str, max_files: int = 4000) -> None:
        self.root = Path(workspace_root).resolve()
        self.max_files = max_files
        self._files_cache: List[Path] | None = None

    @property
    def is_available(self) -> bool:
        return self.root.exists() and self.root.is_dir()

    def build_overview(self, max_files: int = 80, max_extensions: int = 10) -> str:
        files = self._list_files()
        if not files:
            return ""

        extension_counts = Counter(path.suffix.lower() or "<none>" for path in files)
        top_extensions = ", ".join(
            f"{ext}:{count}" for ext, count in extension_counts.most_common(max_extensions)
        )
        sample_files = "\n".join(f"- {self._relative(path)}" for path in files[:max_files])
        return (
            f"Workspace root: {self.root}\n"
            f"Total fichiers indexes: {len(files)}\n"
            f"Extensions principales: {top_extensions or 'n/a'}\n"
            f"Exemples de fichiers:\n{sample_files}"
        ).strip()

    def search(self, query: str, limit: int = 6) -> List[Dict[str, object]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        files = self._list_files()
        if not files:
            return []

        scores: Dict[Path, int] = defaultdict(int)
        reasons: Dict[Path, set[str]] = defaultdict(set)
        snippets: Dict[Path, List[str]] = defaultdict(list)

        for path in files:
            rel_lower = self._relative(path).lower()
            basename_lower = path.name.lower()
            for token in tokens:
                if token in basename_lower:
                    scores[path] += 6
                    reasons[path].add("filename")
                elif token in rel_lower:
                    scores[path] += 3
                    reasons[path].add("filepath")

        content_hits = self._search_contents(tokens)
        for path, matches in content_hits.items():
            scores[path] += 2 * len(matches)
            reasons[path].add("content")
            snippets[path].extend(matches[:2])

        ranked = sorted(scores.keys(), key=lambda path: (-scores[path], self._relative(path)))
        results: List[Dict[str, object]] = []
        for path in ranked[: max(1, limit)]:
            preview = "\n".join(snippets.get(path, [])[:2]).strip()
            if not preview:
                preview = self._build_preview(path, max_chars=700)
            results.append(
                {
                    "path": self._relative(path),
                    "score": scores[path],
                    "reasons": sorted(reasons.get(path, set())),
                    "excerpt": preview,
                }
            )
        return results

    def build_context(
        self,
        query: str,
        limit: int = 4,
        include_overview: bool = False,
        max_file_chars: int = 4000,
    ) -> str:
        if not self.is_available:
            return ""

        results = self.search(query=query, limit=limit)
        parts: List[str] = []
        if include_overview:
            overview = self.build_overview()
            if overview:
                parts.append("Vue d'ensemble du workspace:\n" + overview)

        if not results:
            return "\n\n".join(parts).strip()

        file_sections: List[str] = []
        for item in results:
            rel_path = str(item.get("path", "")).strip()
            if not rel_path:
                continue
            abs_path = (self.root / rel_path).resolve()
            content = self._read_text(abs_path, max_chars=max_file_chars)
            if not content:
                excerpt = str(item.get("excerpt", "")).strip()
                if excerpt:
                    file_sections.append(f"{rel_path}\n```text\n{excerpt}\n```")
                continue
            file_sections.append(f"{rel_path}\n```text\n{content}\n```")

        if file_sections:
            parts.append("Fichiers pertinents du workspace:\n" + "\n\n".join(file_sections))

        return "\n\n".join(part for part in parts if part).strip()

    def collect_targeted_files(
        self,
        query: str,
        limit: int = 3,
        max_file_chars: int = 12000,
    ) -> List[Dict[str, str]]:
        if not self.is_available:
            return []

        selected: List[Path] = []
        seen: set[Path] = set()

        for raw_path in self._extract_candidate_paths(query):
            resolved = self._resolve_candidate_path(raw_path)
            if not resolved or resolved in seen or not self._include_path(resolved):
                continue
            selected.append(resolved)
            seen.add(resolved)
            if len(selected) >= limit:
                break

        if len(selected) < limit:
            for item in self.search(query=query, limit=max(limit * 2, limit)):
                rel_path = str(item.get("path", "")).strip()
                if not rel_path:
                    continue
                resolved = (self.root / rel_path).resolve()
                if resolved in seen or not self._include_path(resolved):
                    continue
                selected.append(resolved)
                seen.add(resolved)
                if len(selected) >= limit:
                    break

        files: List[Dict[str, str]] = []
        for path in selected[: max(1, limit)]:
            content = self._read_text(path, max_chars=max_file_chars)
            if not content:
                continue
            files.append({"path": self._relative(path), "content": content})
        return files

    def _list_files(self) -> List[Path]:
        if self._files_cache is not None:
            return self._files_cache

        if not self.is_available:
            self._files_cache = []
            return self._files_cache

        files = self._list_files_with_rg()
        if files is None:
            files = self._list_files_fallback()
        self._files_cache = files[: self.max_files]
        return self._files_cache

    def _list_files_with_rg(self) -> List[Path] | None:
        try:
            proc = subprocess.run(
                ["rg", "--files", str(self.root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )
        except Exception:
            return None
        if proc.returncode not in {0, 1}:
            return None

        results: List[Path] = []
        for raw_line in proc.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            candidate = Path(line)
            if not candidate.is_absolute():
                candidate = (self.root / candidate).resolve()
            if self._include_path(candidate):
                results.append(candidate)
        return sorted(results, key=lambda path: self._relative(path))

    def _list_files_fallback(self) -> List[Path]:
        results: List[Path] = []
        for current_root, dirs, files in os.walk(self.root):
            dirs[:] = [name for name in dirs if name not in self.EXCLUDED_DIRS]
            current_path = Path(current_root)
            for filename in files:
                candidate = (current_path / filename).resolve()
                if self._include_path(candidate):
                    results.append(candidate)
                    if len(results) >= self.max_files:
                        return sorted(results, key=lambda path: self._relative(path))
        return sorted(results, key=lambda path: self._relative(path))

    def _search_contents(self, tokens: List[str]) -> Dict[Path, List[str]]:
        matches: Dict[Path, List[str]] = defaultdict(list)

        try:
            for token in tokens[:6]:
                proc = subprocess.run(
                    ["rg", "-n", "-S", "-m", "2", "--no-heading", "--color", "never", token, str(self.root)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    check=False,
                )
                if proc.returncode not in {0, 1}:
                    raise RuntimeError("rg unavailable")
                for line in proc.stdout.splitlines():
                    match = re.match(r"^(.*?):(\d+):(.*)$", line)
                    if not match:
                        continue
                    raw_path, line_no, text = match.groups()
                    candidate = Path(raw_path)
                    if not candidate.is_absolute():
                        candidate = (self.root / candidate).resolve()
                    if not self._include_path(candidate):
                        continue
                    snippet = f"L{line_no}: {text.strip()}"
                    if snippet not in matches[candidate]:
                        matches[candidate].append(snippet)
        except Exception:
            scanned = 0
            lowered_tokens = [token.lower() for token in tokens[:4]]
            for path in self._list_files():
                if scanned >= 250:
                    break
                content = self._read_text(path, max_chars=6000)
                if not content:
                    continue
                scanned += 1
                lower_content = content.lower()
                local_matches: List[str] = []
                for token in lowered_tokens:
                    if token in lower_content:
                        local_matches.append(token)
                if local_matches:
                    excerpt = self._build_preview(path, max_chars=400)
                    if excerpt:
                        matches[path].append(excerpt)

        return matches

    def _build_preview(self, path: Path, max_chars: int = 700) -> str:
        content = self._read_text(path, max_chars=max_chars)
        if not content:
            return ""
        return content.strip()

    def _read_text(self, path: Path, max_chars: int = 4000) -> str:
        try:
            if not self._include_path(path):
                return ""
            if path.suffix.lower() in self.BINARY_SUFFIXES:
                return ""
            raw = path.read_bytes()
            if b"\x00" in raw:
                return ""
            text = raw.decode("utf-8", errors="ignore")
            return text[:max_chars].strip()
        except Exception:
            return ""

    def _include_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False
        if not resolved.exists() or not resolved.is_file():
            return False
        if self.root not in resolved.parents and resolved != self.root:
            return False
        if any(part in self.EXCLUDED_DIRS for part in resolved.parts):
            return False
        if resolved.suffix.lower() in self.BINARY_SUFFIXES:
            return False
        return True

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except Exception:
            return path.name

    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        seen = set()
        for token in re.split(r"[\s,;:!?.()/\\\-_]+", (text or "").lower()):
            normalized = token.strip()
            if len(normalized) < 3 or normalized in self.STOPWORDS:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            tokens.append(normalized)
        return tokens

    def _extract_candidate_paths(self, text: str) -> List[str]:
        candidates: List[str] = []
        seen: set[str] = set()
        pattern = re.compile(
            r"(?:[A-Za-z]:[\\/][^\s:\"'<>|]+|(?:[\w.-]+[\\/])+[\w.-]+|[\w.-]+\.[A-Za-z0-9]{1,12})"
        )
        for match in pattern.findall(text or ""):
            candidate = match.strip().strip("`'\"()[]{}<>.,;")
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
        return candidates

    def _resolve_candidate_path(self, raw_path: str) -> Path | None:
        candidate = (raw_path or "").strip()
        if not candidate:
            return None
        try:
            path = Path(candidate)
            resolved = path.resolve() if path.is_absolute() else (self.root / path).resolve()
        except Exception:
            return None
        return resolved
