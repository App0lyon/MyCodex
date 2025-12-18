import re
from typing import Any, Dict


def render(template: str, context: Dict[str, Any]) -> str:
    """
    Replace placeholders like {{KEY}} in the template with context values.
    Missing keys are replaced by an empty string to avoid leaking braces.
    """

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        value = context.get(key, "")
        return "" if value is None else str(value)

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, template)
