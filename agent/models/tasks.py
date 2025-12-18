import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    id: int
    title: str
    description: str
    input: str
    output: str
    dependencies: List[int] = field(default_factory=list)


@dataclass
class FileEdit:
    path: str
    content: str


@dataclass
class ExecutionOutput:
    status: str
    files: List[FileEdit] = field(default_factory=list)
    notes: str = ""
    review: Optional["TaskReview"] = None


@dataclass
class CriticFeedback:
    score: int
    problems: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskReview:
    summary: str = ""
    problems: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


def parse_tasks(raw_tasks: Any) -> List[Task]:
    """Convert raw JSON from the planner into typed tasks."""
    tasks: List[Task] = []
    if not isinstance(raw_tasks, list):
        return tasks

    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        try:
            dependencies_raw = item.get("dependencies", []) or []
            dependencies: List[int] = []
            if isinstance(dependencies_raw, list):
                for dep in dependencies_raw:
                    try:
                        dependencies.append(int(dep))
                    except Exception:
                        continue

            tasks.append(
                Task(
                    id=int(item.get("id")),
                    title=str(item.get("title", "")).strip(),
                    description=str(item.get("description", "")).strip(),
                    input=str(item.get("input", "")).strip(),
                    output=str(item.get("output", "")).strip(),
                    dependencies=dependencies,
                )
            )
        except Exception:
            # Skip malformed tasks silently to keep the pipeline resilient.
            continue
    return tasks


def parse_execution_output(raw: Dict[str, Any]) -> ExecutionOutput:
    files_data = raw.get("files") or []
    files: List[FileEdit] = []
    for file_entry in files_data:
        if isinstance(file_entry, dict) and "path" in file_entry and "content" in file_entry:
            files.append(FileEdit(path=str(file_entry["path"]), content=str(file_entry["content"])))

    def _normalize_status(value: Any) -> str:
        label = str(value or "").strip().lower()
        if label in {"success", "ok", "done", "completed", "terminé", "termine", "terminee"}:
            return "success"
        if label in {"failure", "failed", "error", "ko"}:
            return "failure"
        # Default: consider it success if code files exist, otherwise failure.
        return "success" if files else "failure"

    return ExecutionOutput(
        status=_normalize_status(raw.get("status")),
        files=files,
        notes=str(raw.get("notes", "")),
        review=parse_task_review(raw.get("review")) if raw.get("review") else None,
    )


def parse_critic_feedback(raw: Dict[str, Any]) -> CriticFeedback:
    def _parse_score(value: Any) -> int:
        """
        Convert a free-form score into an int.
        Accepts ints/floats, or extracts the first integer found in a string like "8/10".
        """
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"-?\d+", value)
            if match:
                try:
                    return int(match.group(0))
                except Exception:
                    return 0
        return 0

    score = _parse_score(raw.get("score", raw.get("global_score", 0)))
    problems = raw.get("problems") or raw.get("issues") or raw.get("problems_detected") or []
    recommendations = raw.get("recommendations") or raw.get("suggestions") or []
    problems_list = [str(item) for item in problems] if isinstance(problems, list) else [str(problems)]
    rec_list = [str(item) for item in recommendations] if isinstance(recommendations, list) else [str(recommendations)]
    return CriticFeedback(score=score, problems=problems_list, recommendations=rec_list, raw=raw)


def parse_task_review(raw: Any) -> Optional[TaskReview]:
    if not isinstance(raw, dict):
        return None
    summary = str(raw.get("summary", raw.get("comment", "")) or "").strip()
    problems = raw.get("problems") or raw.get("issues") or []
    recommendations = raw.get("recommendations") or raw.get("suggestions") or []
    problems_list = [str(item) for item in problems] if isinstance(problems, list) else [str(problems)]
    rec_list = [str(item) for item in recommendations] if isinstance(recommendations, list) else [str(recommendations)]
    return TaskReview(summary=summary, problems=problems_list, recommendations=rec_list, raw=raw)
