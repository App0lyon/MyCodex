from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from models.tasks import FileEdit


@dataclass
class ApplyOutcome:
    normalized_files: List[FileEdit] = field(default_factory=list)
    applied_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class WorkspacePatchApplier:
    def __init__(self, workspace_root: str) -> None:
        self.root = Path(workspace_root).resolve()

    @property
    def is_available(self) -> bool:
        return self.root.exists() and self.root.is_dir()

    def apply_edits(self, edits: Iterable[FileEdit]) -> ApplyOutcome:
        outcome = ApplyOutcome()
        if not self.is_available:
            outcome.errors.append("Workspace indisponible pour appliquer les fichiers.")
            return outcome

        for edit in edits:
            raw_path = str(edit.path or "").strip()
            if not raw_path:
                outcome.errors.append("Chemin de fichier vide refuse.")
                continue

            target = self._resolve_target(raw_path)
            if target is None:
                outcome.errors.append(f"Chemin hors workspace refuse: {raw_path}")
                continue

            if target.exists() and not target.is_file():
                outcome.errors.append(f"Cible non fichier refusee: {raw_path}")
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(edit.content or ""), encoding="utf-8")
                rel_path = target.relative_to(self.root).as_posix()
                normalized = FileEdit(path=rel_path, content=str(edit.content or ""))
                outcome.normalized_files.append(normalized)
                outcome.applied_files.append(rel_path)
            except Exception as exc:
                outcome.errors.append(f"Echec ecriture {raw_path}: {exc}")

        return outcome

    def _resolve_target(self, raw_path: str) -> Path | None:
        try:
            candidate = Path(raw_path)
            resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
            resolved.relative_to(self.root)
        except Exception:
            return None
        return resolved
