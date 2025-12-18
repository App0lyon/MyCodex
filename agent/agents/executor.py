import json
import re
from typing import List, Optional

from clients.ollama_client import OllamaClient
from models.tasks import ExecutionOutput, FileEdit, Task, parse_execution_output
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class Executor:
    def __init__(self, client: OllamaClient, model: str = "codellama:13b") -> None:
        self.client = client
        self.model = model

    def execute(
        self,
        task: Task,
        project_context: str = "",
        existing_code: Optional[str] = "",
        constraints: Optional[str] = "",
        scenario_id: str | None = None,
    ) -> ExecutionOutput:
        user_prompt = render(
            UserPrompts.EXECUTOR,
            {
                "TASK_JSON": json.dumps(task.__dict__, ensure_ascii=False, indent=2),
                "PROJECT_CONTEXT": project_context or "",
                "EXISTING_CODE": existing_code or "",
                "CONSTRAINTS": constraints or "",
            },
        )

        raw_content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.EXECUTOR.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes=f"executor.execute task={task.id}",
        )
        # print("[Executor][debug] raw:", raw_content)

        try:
            raw = json.loads(raw_content)
        except json.JSONDecodeError:
            raw = {}
            output = ExecutionOutput(status="failure", notes="Executor returned non-JSON output")
        else:
            output = parse_execution_output(raw)

        if not output.files:
            extracted = self._extract_code_blocks(raw_content)
            if extracted:
                output.files.extend(extracted)
        if not output.files:
            output.status = "failure"
            if not output.notes:
                output.notes = "Aucun code retourne par le modele (fichiers vides)"
        else:
            status_label = (output.status or "").strip().lower()
            if status_label not in {"success", "failure"}:
                output.status = "success"
        return output

    def _extract_code_blocks(self, text: str) -> List[FileEdit]:
        """
        Extract fenced code blocks, trying to infer a path if it precedes the fence.
        """
        files: List[FileEdit] = []
        if not text:
            return files

        pattern_with_path = re.compile(
            r"(?P<path>[\w./-]+):\s*```[a-zA-Z0-9]*\s*(?P<code>[\s\S]*?)```",
            re.MULTILINE,
        )
        for match in pattern_with_path.finditer(text):
            path = match.group("path").strip()
            code = match.group("code")
            files.append(FileEdit(path=path, content=code))

        if files:
            return files

        generic_block = re.search(r"```[a-zA-Z0-9]*\s*([\s\S]*?)```", text)
        if generic_block:
            files.append(FileEdit(path="model_output.py", content=generic_block.group(1)))

        return files
