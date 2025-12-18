from __future__ import annotations

from typing import Dict, List

from clients.search_client import WebSearchClient


class Searcher:
    def __init__(self, client: WebSearchClient) -> None:
        self.client = client

    def search(self, query: str, max_results: int = 5) -> Dict[str, object]:
        """
        Effectue une recherche web (DuckDuckGo API) et renvoie une structure simple.
        """
        results = self.client.search(query=query, max_results=max_results)
        lines: List[str] = []
        for item in results:
            title = item.get("title") or "Resultat"
            url = item.get("url") or ""
            excerpt = item.get("excerpt") or ""
            snippet = (excerpt[:300] + "…") if len(excerpt) > 300 else excerpt
            lines.append(f"- {title} — {url}\n  {snippet}".strip())

        return {
            "query": query,
            "results": results,
            "context": "\n".join(lines).strip(),
        }
