import uuid
from typing import Any, Dict, List, Optional

import requests

from utils.cost_logger import CostLogger, utc_ms


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 180,
        cost_logger: Optional[CostLogger] = None,
        costs_path: str = "costs.csv",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_scenario_id: Optional[str] = None
        self.cost_logger = cost_logger or CostLogger(path=costs_path)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        stream: bool = False,
        extra_options: Optional[Dict[str, Any]] = None,
        scenario_id: Optional[str] = None,
        call_id: Optional[str] = None,
        notes: str = "",
        endpoint: str = "/api/chat",
    ) -> str:
        """Call Ollama chat endpoint and return the content string."""
        options = {"temperature": temperature}
        if extra_options:
            options.update(extra_options)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options,
        }

        call_identifier = call_id or str(uuid.uuid4())
        scenario_label = (scenario_id or self.default_scenario_id or "").strip() or "unknown"
        prompt_text = self._flatten_messages(messages)
        prompt_hash = self.cost_logger.hash_prompt(prompt_text) if self.cost_logger else ""
        prompt_tokens = self.cost_logger.count_tokens(model, prompt_text) if self.cost_logger else 0
        start_ms = utc_ms()
        status_label = "success"

        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # For non-streaming responses, Ollama returns the final message content.
            content = data.get("message", {}).get("content")
            if content is None:
                status_label = "error:missing_content"
                raise ValueError("Ollama chat response missing message content")

            completion_tokens = int(data.get("eval_count") or 0)
            prompt_tokens_api = data.get("prompt_eval_count")
            if prompt_tokens_api is not None:
                prompt_tokens = int(prompt_tokens_api)
            if completion_tokens == 0 and self.cost_logger:
                completion_tokens = self.cost_logger.count_tokens(model, content)

            latency_ms = max(0, utc_ms() - start_ms)
            if self.cost_logger:
                self.cost_logger.log_success(
                    scenario_id=scenario_label,
                    call_id=call_identifier,
                    model=model,
                    endpoint=f"{self.base_url}{endpoint}",
                    prompt_hash=prompt_hash,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    status=status_label,
                    notes=notes,
                )
            return content
        except Exception as exc:
            latency_ms = max(0, utc_ms() - start_ms)
            status_label = status_label if status_label.startswith("error:") else f"error:{exc.__class__.__name__}"
            if self.cost_logger:
                self.cost_logger.log_failure(
                    scenario_id=scenario_label,
                    call_id=call_identifier,
                    model=model,
                    endpoint=f"{self.base_url}{endpoint}",
                    prompt_hash=prompt_hash,
                    prompt_tokens=prompt_tokens,
                    latency_ms=latency_ms,
                    error=exc,
                    notes=notes or status_label,
                )
            raise

    def set_default_scenario(self, scenario_id: Optional[str]) -> None:
        self.default_scenario_id = (scenario_id or "").strip() or None

    def _flatten_messages(self, messages: List[Dict[str, str]]) -> str:
        return "\n".join(f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in messages if isinstance(msg, dict))
