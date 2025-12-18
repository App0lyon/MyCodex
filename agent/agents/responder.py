import json
from typing import Dict, List

from clients.ollama_client import OllamaClient
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class Responder:
    def __init__(self, client: OllamaClient, model: str = "gemma3:4b") -> None:
        self.client = client
        self.model = model

    def build_markdown_response(
        self,
        goal: str,
        context: str,
        tasks: List[Dict[str, object]],
        unresolved_tasks: List[Dict[str, object]],
        final_critic: Dict[str, object],
        scenario_id: str | None = None,
    ) -> str:
        user_prompt = render(
            UserPrompts.RESPONDER,
            {
                "GOAL": goal,
                "CONTEXT": context or "Non precise",
                "TASK_RESULTS": json.dumps(tasks, ensure_ascii=False, indent=2),
                "UNRESOLVED_TASKS": json.dumps(unresolved_tasks, ensure_ascii=False, indent=2),
                "FINAL_CRITIC": json.dumps(final_critic, ensure_ascii=False, indent=2),
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.RESPONDER.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.2,
            scenario_id=scenario_id,
            notes="responder.build_markdown_response",
        )
        return content.strip()
