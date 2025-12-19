import ast
import json
import re
from typing import List, Optional

from clients.ollama_client import OllamaClient
from models.tasks import Task, parse_tasks
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class Planner:
    def __init__(self, client: OllamaClient, model: str = "llama3.1:8b") -> None:
        self.client = client
        self.model = model

    def plan(self, goal: str, context: str = "", constraints: str = "", scenario_id: str | None = None) -> List[Task]:
        user_prompt = render(
            UserPrompts.PLANNER,
            {
                "GOAL": goal,
                "CONTEXT": context or "",
                "CONSTRAINTS": constraints or "",
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.PLANNER.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes="planner.plan",
        )
        # print("[Planner][debug] raw:", content)

        raw = self._parse_json_array(content)
        if raw is None:
            return []

        return parse_tasks(raw)

    def _parse_json_array(self, text: str) -> Optional[List[dict]]:
        """
        Extract and load a JSON array from the model output.
        Handles fenced blocks, leading/trailing prose and mildly invalid JSON by
        falling back to literal_eval with null/true/false normalization.
        """
        if not text:
            return None

        candidates = []

        # 1) fenced ```json ... ``` block
        fenced = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, flags=re.IGNORECASE)
        candidates.extend(fenced)

        # 2) first/last bracket in the whole text
        bracket_match = re.search(r"\[[\s\S]*\]", text)
        if bracket_match:
            candidates.append(bracket_match.group(0))

        # 3) raw text as a last resort
        candidates.append(text)

        for candidate in candidates:
            parsed = self._try_parse_array(candidate)
            if parsed is not None:
                return parsed
        return None

    def _try_parse_array(self, candidate: str) -> Optional[List[dict]]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Tolerate null/true/false and simple Python literals
        sanitized = re.sub(r"\bnull\b", "None", candidate, flags=re.IGNORECASE)
        sanitized = re.sub(r"\btrue\b", "True", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\bfalse\b", "False", sanitized, flags=re.IGNORECASE)
        try:
            parsed = ast.literal_eval(sanitized)
            return parsed if isinstance(parsed, list) else None
        except Exception:
            return None
