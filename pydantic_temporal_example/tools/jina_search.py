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
    )                    if line.startswith("data:"):
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
