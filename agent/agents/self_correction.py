import json
from typing import List
from clients.ollama_client import OllamaClient
from models.tasks import CriticFeedback, ExecutionOutput, FileEdit, Task, parse_execution_output
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class SelfCorrection:
    def __init__(self, client: OllamaClient, model: str = "codellama:13b") -> None:
        self.client = client
        self.model = model

    def correct(
        self,
        task: Task,
        current_output: ExecutionOutput,
        critic_feedback: CriticFeedback,
        scenario_id: str | None = None,
    ) -> ExecutionOutput:
        current_code_json = json.dumps(
            {
                "status": current_output.status,
                "notes": current_output.notes,
                "files": [{"path": f.path, "content": f.content} for f in current_output.files],
            },
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = render(
            UserPrompts.EXECUTOR_SELF_CORRECTION,
            {
                "TASK_JSON": json.dumps(task.__dict__, ensure_ascii=False, indent=2),
                "CURRENT_CODE": current_code_json,
                "CRITIC_FEEDBACK": json.dumps(
                    critic_feedback.raw or critic_feedback.__dict__,
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.EXECUTOR_SELF_CORRECTION.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes=f"self_correction task={task.id}",
        )
        # print("[SelfCorrection][debug] raw:", content)

        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            return ExecutionOutput(status="failure", notes="Self-correction returned non-JSON output", files=[])

        output = parse_execution_output(raw)

        if not output.files:
            extracted = self._extract_code_blocks(content)
            if extracted:
                output.files.extend(extracted)

        if not output.files:
            output.status = "failure"
            if not output.notes:
                output.notes = "Aucun code retourne par la self-correction"

        return output

    def _extract_code_blocks(self, text: str) -> List[FileEdit]:
        """
        Reprend l'extraction des blocs de code pour capturer un fichier meme si le JSON est incomplet.
        """
        import re

        files: list[FileEdit] = []
        if not text:
            return files

        pattern_with_path = re.compile(
            r"(?P<path>[\\w./-]+):\\s*```[a-zA-Z0-9]*\\s*(?P<code>[\\s\\S]*?)```",
            re.MULTILINE,
        )
        for match in pattern_with_path.finditer(text):
            path = match.group("path").strip()
            code = match.group("code")
            files.append(FileEdit(path=path, content=code))

        if files:
            return files

        generic_block = re.search(r"```[a-zA-Z0-9]*\\s*([\\s\\S]*?)```", text)
        if generic_block:
            files.append(FileEdit(path="self_correction_output.py", content=generic_block.group(1)))

        return files
