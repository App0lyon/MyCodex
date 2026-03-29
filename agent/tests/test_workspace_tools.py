from pathlib import Path

from models.tasks import FileEdit
from utils.workspace_context import WorkspaceContextBuilder
from utils.workspace_patcher import WorkspacePatchApplier


def test_collect_targeted_files_prefers_explicit_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "src" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('hello')\n", encoding="utf-8")

    builder = WorkspaceContextBuilder(str(workspace))

    results = builder.collect_targeted_files("Merci de lire src/module.py", limit=1)

    assert len(results) == 1
    assert results[0]["path"] == "src/module.py"
    assert "print('hello')" in results[0]["content"]


def test_workspace_patch_applier_writes_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    applier = WorkspacePatchApplier(str(workspace))

    outcome = applier.apply_edits([FileEdit(path="app/main.py", content="value = 1\n")])

    target = workspace / "app" / "main.py"
    assert outcome.errors == []
    assert outcome.applied_files == ["app/main.py"]
    assert target.read_text(encoding="utf-8") == "value = 1\n"


def test_workspace_patch_applier_rejects_path_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    applier = WorkspacePatchApplier(str(workspace))

    outcome = applier.apply_edits([FileEdit(path="../escape.py", content="boom\n")])

    assert outcome.applied_files == []
    assert outcome.normalized_files == []
    assert outcome.errors
    assert not (tmp_path / "escape.py").exists()
