from __future__ import annotations

from typing import Any, Dict, List

import requests


class WebSearchClient:
    """
    Client HTTP minimaliste pour interroger l'API publique DuckDuckGo (instant answer).
    Cette API ne necessite pas de cle et fournit des resultats courts.
    """

    def __init__(self, base_url: str = "https://api.duckduckgo.com", timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        params = {
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "skip_disambig": 1,
        }
        resp = requests.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict[str, str]] = []

        def _add(item: Dict[str, Any]) -> None:
            title = str(item.get("Text") or item.get("Result") or item.get("Heading") or "").strip()
            url = str(item.get("FirstURL") or item.get("AbstractURL") or item.get("URL") or "").strip()
            excerpt = str(item.get("AbstractText") or item.get("Text") or item.get("Description") or "").strip()
            if not (title or excerpt):
                return
            results.append({"title": title or excerpt[:80], "url": url, "excerpt": excerpt})

        # Abstract section
        if data.get("AbstractText") or data.get("Heading"):
            _add({"Text": data.get("Heading") or "", "FirstURL": data.get("AbstractURL"), "AbstractText": data.get("AbstractText")})

        # Main results (rarely populated)
        for item in data.get("Results") or []:
            if isinstance(item, dict):
                _add(item)

        # Related topics
        for topic in data.get("RelatedTopics") or []:
            if isinstance(topic, dict):
                if "Topics" in topic and isinstance(topic["Topics"], list):
                    for sub in topic["Topics"]:
                        if isinstance(sub, dict):
                            _add(sub)
                else:
                    _add(topic)

        return results[: max_results or 5]
