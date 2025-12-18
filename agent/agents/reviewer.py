import json
from typing import List

from clients.ollama_client import OllamaClient
from models.tasks import ExecutionOutput, Task, TaskReview, parse_task_review
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class Reviewer:
    def __init__(self, client: OllamaClient, model: str = "qwen2.5") -> None:
        self.client = client
        self.model = model

    def review(
        self,
        task: Task,
        execution: ExecutionOutput,
        context: str = "",
        constraints: str = "",
        scenario_id: str | None = None,
    ) -> TaskReview:
        code_blocks: List[str] = []
        for file_edit in execution.files:
            code_blocks.append(f"{file_edit.path}:\n{file_edit.content}")
        code_text = "\n\n".join(code_blocks) if code_blocks else "Aucun fichier de code fourni."

        execution_json = json.dumps(
            {
                "status": execution.status,
                "notes": execution.notes,
                "files": [{"path": f.path, "content": f.content} for f in execution.files],
            },
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = render(
            UserPrompts.TASK_REVIEW,
            {
                "TASK_JSON": json.dumps(task.__dict__, ensure_ascii=False, indent=2),
                "CONTEXT": context or "",
                "CONSTRAINTS": constraints or "",
                "EXECUTION_JSON": execution_json,
                "CODE_BLOCKS": code_text,
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.TASK_REVIEW.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes=f"reviewer.review task={task.id}",
        )
        # print("[Reviewer][debug] raw:", content)

        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            return TaskReview(
                summary="Review non JSON",
                problems=["Reviewer returned non-JSON output"],
                recommendations=[],
                raw={},
            )

        review = parse_task_review(raw)
        if review is None:
            return TaskReview(
                summary="Review invalide",
                problems=["Reviewer returned invalid format"],
                recommendations=[],
                raw=raw if isinstance(raw, dict) else {},
            )
        return review
