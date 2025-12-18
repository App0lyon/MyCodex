import re

from clients.ollama_client import OllamaClient
from prompts import SystemPrompts, UserPrompts
from utils.prompt_renderer import render


class PromptOptimizer:
    def __init__(self, client: OllamaClient, model: str = "gemma3:4b") -> None:
        self.client = client
        self.model = model

    def optimize(self, prompt: str, context: str = "", scenario_id: str | None = None) -> tuple[str, str]:
        """
        Returns (optimized_prompt, raw_model_output).
        """
        user_prompt = render(
            UserPrompts.OPTIMIZER,
            {
                "PROMPT": prompt,
                "CONTEXT": context or "",
            },
        )

        content = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SystemPrompts.OPTIMIZER.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            scenario_id=scenario_id,
            notes="prompt_optimizer.optimize",
        )

        optimized = self._extract_prompt(content)
        return optimized.strip(), content

    def _extract_prompt(self, text: str) -> str:
        """
        Prefer the first fenced block, otherwise return the raw text.
        """
        fenced = re.findall(r"```(?:text|prompt)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
        if fenced:
            return fenced[0]
        return text
