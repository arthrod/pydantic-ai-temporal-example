import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

import httpx
from pydantic import TypeAdapter
from pydantic_ai.tools import Tool
from typing_extensions import TypedDict

__all__ = ('jina_search_tool',)


class JinaSearchResult(TypedDict):
    """A Jina search result.
    
    See Jina AI Search and DeepSearch API documentation for more information.
    """

    title: str
    """The title of the search result."""
    url: str
    """The URL of the search result."""
    content: str
    """A short description of the search result."""
    score: float
    """The relevance score of the search result."""


jina_search_ta = TypeAdapter(list[JinaSearchResult])


@dataclass
class JinaSearchTool:
    """The Jina search tool."""

    api_key: str
    """The Jina API key."""

    def _build_time_range_filter(self, time_range: str | None) -> str:
        """Build SERP-compatible time filter for basic search."""
        if not time_range:
            return ""
        
        # Map time_range to date calculations
        time_map = {
            'day': 1,
            'd': 1,
            'week': 7,
            'w': 7,
            'month': 30,
            'm': 30,
            'year': 365,
            'y': 365,
        }
        
        days = time_map.get(time_range, 0)
        if days:
            target_date = datetime.now() - timedelta(days=days)
            return f" after:{target_date.strftime('%Y-%m-%d')}"
        return ""

    def _append_time_range_to_prompt(self, query: str, time_range: str | None) -> str:
        """Append time range instruction to prompt for advanced search."""
        if not time_range:
            return query
        
        time_descriptions = {
            'day': 'from the last day',
            'd': 'from the last day',
            'week': 'from the last week',
            'w': 'from the last week',
            'month': 'from the last month',
            'm': 'from the last month',
            'year': 'from the last year',
            'y': 'from the last year',
        }
        
        time_desc = time_descriptions.get(time_range, '')
        if time_desc:
            return f"{query} (Focus on information {time_desc})"
        return query

    async def __call__(
        self,
        query: str,
        search_deep: Literal['basic', 'advanced'] = 'basic',
        topic: Literal['general', 'news'] = 'general',
        time_range: Literal['day', 'week', 'month', 'year', 'd', 'w', 'm', 'y'] | None = None,
    ):
        """Searches Jina for the given query and returns the results.

        Args:
            query: The search query to execute with Jina.
            search_deep: The depth of the search.
            topic: The category of the search.
            time_range: The time range back from the current date to filter results.

        Returns:
            The search results.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            if search_deep == "advanced":
                # Use the DeepSearch API with time range appended to prompt
                enhanced_query = self._append_time_range_to_prompt(query, time_range)
                headers["Content-Type"] = "application/json"
                
                async with client.stream(
                    "POST",
                    "https://deepsearch.jina.ai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "jina-deepsearch-v1",
                        "messages": [{"role": "user", "content": enhanced_query}],
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    full_content = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                chunk_str = line[len("data: ") :]
                                if chunk_str.strip() == "[DONE]":
                                    continue
                                chunk = json.loads(chunk_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    if "content" in delta:
                                        full_content += delta["content"]
                                    # DeepSearch may stream reasoning content separately
                                    if "reasoning_content" in delta:
                                        full_content += delta["reasoning_content"]
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue  # Ignore invalid JSON lines

                results = [
                    {
                        "title": f"DeepSearch Result for: {query}",
                        "url": "",
                        "content": full_content,
                        "score": 0.0,
                    }
                ]
            else:
                # Use the standard Search API with GET request and SERP-style time filtering
                enhanced_query = query + self._build_time_range_filter(time_range)
                headers["X-Return-Format"] = "markdown"
                
                # Use GET with query parameter
                response = await client.get(
                    "https://s.jina.ai/",
                    headers=headers,
                    params={"q": enhanced_query},
                )
                response.raise_for_status()
                data = response.json()

                # Parse results from the response
                # Jina Search API returns results in 'data' field
                raw_results = data.get("data", [])
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": float(item.get("score", 0.0)),
                    }
                    for item in raw_results
                ]

        return jina_search_ta.validate_python(results)


def jina_search_tool(api_key: str):
    """Creates a Jina search tool.

    Args:
        api_key: The Jina API key.

            You can get one by signing up at https://jina.ai

    Returns:
        Tool[Any]: A Tool configured to execute Jina searches.
    """
    return Tool[Any](
        JinaSearchTool(api_key=api_key).__call__,
        name="jina_search",
        description="Searches Jina for the given query and returns the results.",
    )
