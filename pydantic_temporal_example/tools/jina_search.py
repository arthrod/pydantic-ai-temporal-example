import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import TypeAdapter
from pydantic_ai.tools import Tool
from typing_extensions import TypedDict


class JinaSearchResult(TypedDict):
    """A Jina search result."""

    title: str
    url: str
    content: str
    score: float


jina_search_ta = TypeAdapter(list[JinaSearchResult])


@dataclass
class JinaSearchTool:
    """The Jina search tool."""

    client: httpx.AsyncClient
    api_key: str

    async def __call__(
        self,
        query: str,
        search_deep: Literal["basic", "advanced"] = "basic",
        topic: Literal["general", "news"] = "general",
        time_range: Literal["day", "week", "month", "year", "d", "w", "m", "y"] | None = None,
    ):
        """
        Perform a Jina search for the given query using either basic or advanced mode.
        
        Parameters:
            query (str): The search query text.
            search_deep (Literal["basic", "advanced"]): If "basic", use the standard search endpoint that returns multiple markdown-formatted results; if "advanced", use the DeepSearch streaming endpoint and aggregate its response into a single result.
            topic (Literal["general", "news"]): Optional topic hint; accepted but not used by the current implementation.
            time_range (Literal["day", "week", "month", "year", "d", "w", "m", "y"] | None): Optional time-range hint; accepted but not used by the current implementation.
        
        Returns:
            list[dict]: A validated list of search result objects with keys:
                - title (str): Result title.
                - url (str): Result URL (empty string when not provided).
                - content (str): Result content or aggregated DeepSearch content.
                - score (float): Relevance score (defaults to 0.0 when not provided).
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if search_deep == "advanced":
            # Use the DeepSearch API
            async with self.client.stream(
                "POST",
                "https://deepsearch.jina.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "jina-deepsearch-v1",
                    "messages": [{"role": "user", "content": query}],
                    "stream": True,
                },
                timeout=120,
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
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                full_content += delta["content"]
                        except json.JSONDecodeError:
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
            # Use the standard Search API
            headers["X-Return-Format"] = "markdown"
            response = await self.client.post("https://s.jina.ai/", headers=headers, json={"q": query})
            response.raise_for_status()
            data = response.json()

            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                }
                for item in data.get("data", [])
            ]

        return jina_search_ta.validate_python(results)


def jina_search_tool(api_key: str):
    """
    Create a Tool that performs searches against Jina.
    
    Parameters:
        api_key (str): API key used to authenticate requests to Jina.
    
    Returns:
        Tool[Any]: A Tool named "jina_search" configured to execute Jina searches and return validated search results.
    """
    return Tool[Any](
        JinaSearchTool(client=httpx.AsyncClient(), api_key=api_key).__call__,
        name="jina_search",
        description="Searches Jina for the given query and returns the results.",
    )