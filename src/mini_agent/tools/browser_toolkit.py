"""Browser toolkit using browser-use for Mini Agent G4."""

import asyncio
from typing import Optional
from agno.tools import tool

try:
    from browser_use import Agent as BrowserAgent
    from browser_use.browser import BrowserSession
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    BrowserAgent = None
    BrowserSession = None


def _get_browser_llm(config):
    """Create a browser-use LLM from the same model config."""
    provider = (config.model_provider or "lmstudio").lower()
    model_id = config.model_id or "qwen3.5-35b"

    if provider == "openai":
        from browser_use.llm.openai.chat import ChatOpenAI
        return ChatOpenAI(id=model_id)
    elif provider == "anthropic":
        from browser_use.llm.anthropic.chat import ChatAnthropic
        return ChatAnthropic(id=model_id)
    elif provider == "ollama":
        from browser_use.llm.ollama.chat import ChatOllama
        return ChatOllama(model=model_id)
    elif provider == "deepseek":
        from browser_use.llm.deepseek.chat import ChatDeepSeek
        return ChatDeepSeek(id=model_id)
    elif provider == "groq":
        from browser_use.llm.groq.chat import ChatGroq
        return ChatGroq(id=model_id)
    elif provider == "lmstudio":
        from browser_use.llm.openai.chat import ChatOpenAI
        return ChatOpenAI(
            id=model_id,
            base_url="http://localhost:1234/v1",
            api_key="local",
        )
    return None


def _run_browser_task(task: str, config) -> str:
    """Run a browser-use task synchronously and return the result."""
    if not BROWSER_USE_AVAILABLE:
        return ("Error: browser-use not installed. "
                "Run: uv add browser-use && uv run playwright install chromium")

    llm = _get_browser_llm(config)
    if llm is None:
        return "Error: no compatible LLM found for browser-use"

    session = BrowserSession()
    agent = BrowserAgent(
        task=task,
        llm=llm,
        browser_session=session,
        use_vision=True,
        max_steps=20,
    )

    try:
        history = asyncio.run(agent.run(max_steps=20))
        if not history:
            return "Browser interaction completed with no result"

        # Collect results from the last few steps
        results = []
        for item in reversed(list(history)):
            result = getattr(item, "result", None)
            if result:
                results.append(str(result))
                if len(results) >= 3:
                    break

        if results:
            return "\n\n".join(results)
        return "No result extracted from browser interaction"
    except Exception as e:
        return f"Browser error: {e}"


class BrowserToolkit:
    """Toolkit for browser automation using browser-use."""

    def __init__(self, config=None):
        self.config = config

    @tool
    def browse_url(self, url: str, task: str = "") -> str:
        """Open a URL in a browser and optionally perform a task on the page.

        Args:
            url: The URL to open (e.g. 'https://example.com')
            task: What to do on the page, e.g. 'find the price',
                  'extract all article titles', 'find contact email'

        Returns:
            The result of the browser interaction
        """
        if not BROWSER_USE_AVAILABLE:
            return ("Error: browser-use not installed. "
                    "Run: uv add browser-use && uv run playwright install chromium")

        if not url:
            return "Error: URL is required"

        full_task = (
            f"Go to {url} and do the following: {task}. "
            "Report what you found."
        ) if task else f"Browse {url} and summarize the main content."

        return _run_browser_task(full_task, self.config)

    @tool
    def search_browser(self, query: str, max_results: int = 5) -> str:
        """Search the web using a browser and return results.

        Args:
            query: The search query
            max_results: Maximum number of results to return (default 5)

        Returns:
            Search results from the web as a list
        """
        if not BROWSER_USE_AVAILABLE:
            return ("Error: browser-use not installed. "
                    "Run: uv add browser-use && uv run playwright install chromium")

        if not query:
            return "Error: query is required"

        task = (
            f"Search DuckDuckGo for '{query}'. "
            f"Extract the first {max_results} search results with their titles and URLs. "
            "Format as a list."
        )
        return _run_browser_task(task, self.config)

    @tool
    def extract_from_page(self, url: str, extraction_goal: str) -> str:
        """Extract specific structured information from a web page.

        Args:
            url: The URL to extract from
            extraction_goal: What to extract, e.g.
                'all email addresses',
                'the price and product name',
                'all heading tags and their text'

        Returns:
            The extracted information
        """
        if not BROWSER_USE_AVAILABLE:
            return ("Error: browser-use not installed. "
                    "Run: uv add browser-use && uv run playwright install chromium")

        if not url:
            return "Error: URL is required"

        task = f"Go to {url} and extract: {extraction_goal}. Report what you found."
        return _run_browser_task(task, self.config)

    @tool
    def browser_status(self) -> str:
        """Check if browser-use is available and working.

        Returns:
            Status of the browser toolkit
        """
        if not BROWSER_USE_AVAILABLE:
            return ("browser-use: NOT AVAILABLE\n"
                    "Install with: uv add browser-use && uv run playwright install chromium")
        return "browser-use: AVAILABLE — each browser task launches a fresh session"
