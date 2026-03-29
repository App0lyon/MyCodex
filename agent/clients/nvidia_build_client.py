import uuid
from typing import Any, Dict, List, Optional

import requests

from utils.cost_logger import CostLogger, utc_ms


class NvidiaBuildClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout: int = 180,
        cost_logger: Optional[CostLogger] = None,
        costs_path: str = "costs.csv",
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_scenario_id: Optional[str] = None
        self.cost_logger = cost_logger or CostLogger(path=costs_path)

        if not self.api_key:
            raise ValueError("NVIDIA Build API key missing. Set --nvidia-api-key or NVIDIA_BUILD_API_KEY.")

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
        endpoint: str = "/chat/completions",
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if extra_options:
            payload.update(extra_options)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices") or []
            if not choices:
                status_label = "error:missing_choices"
                raise ValueError("NVIDIA Build response missing choices")

            message = choices[0].get("message") or {}
            content = self._normalize_content(message.get("content"))
            if not content:
                status_label = "error:missing_content"
                raise ValueError("NVIDIA Build response missing message content")

            usage = data.get("usage") or {}
            prompt_tokens_api = usage.get("prompt_tokens")
            completion_tokens = int(usage.get("completion_tokens") or 0)
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

    def _normalize_content(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: List[str] = []
            for item in value:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                    elif "content" in item:
                        parts.append(str(item.get("content", "")))
                elif item is not None:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part).strip()
        return "" if value is None else str(value)
