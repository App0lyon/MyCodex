import json
import re
from typing import Dict, List, Optional

from clients.ollama_client import OllamaClient
from models.tasks import CriticFeedback, parse_critic_feedback
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class Critic:
    def __init__(self, client: OllamaClient, model: str = "qwen2.5") -> None:
        self.client = client
        self.model = model

    def evaluate_final(
        self,
        goal: str,
        context: str,
        constraints: str,
        task_results: List[Dict[str, object]],
        unresolved_tasks: List[Dict[str, object]],
        scenario_id: str | None = None,
    ) -> CriticFeedback:
        user_prompt = render(
            UserPrompts.CRITIC,
            {
                "GOAL": goal,
                "CONTEXT": context,
                "CONSTRAINTS": constraints,
                "TASK_RESULTS": json.dumps(task_results, ensure_ascii=False, indent=2),
                "UNRESOLVED_TASKS": json.dumps(unresolved_tasks, ensure_ascii=False, indent=2),
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.CRITIC.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes="critic.evaluate_final",
        )
        # print("[Critic][debug] raw:", content)

        raw = self._parse_json_object(content)
        if raw is None:
            return CriticFeedback(score=0, problems=["Critic returned non-JSON output"], recommendations=[], raw={})

        return parse_critic_feedback(raw)

    def _parse_json_object(self, text: str) -> Optional[Dict[str, object]]:
        """
        Extract and load a JSON object from the model output.
        Handles fenced ```json blocks and leading/trailing prose.
        """
        if not text:
            return None

        # Fenced block
        fenced = re.findall(r"```(?:json)?\s*({[\s\S]*?})\s*```", text, flags=re.IGNORECASE)
        candidates = list(fenced)

        # First/last brace in the whole text
        brace_match = re.search(r"{[\s\S]*}", text)
        if brace_match:
            candidates.append(brace_match.group(0))

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
