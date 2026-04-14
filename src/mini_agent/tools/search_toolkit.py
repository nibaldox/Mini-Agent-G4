"""Custom search toolkit for Mini Agent G4"""

from typing import Literal, Optional

from agno.tools.websearch import WebSearchTools as AgnoWebSearchTools


class SearchToolkit(AgnoWebSearchTools):
    """Extended web search toolkit for MiniAgent."""

    def __init__(
        self,
        enable_search: bool = True,
        enable_news: bool = False,
        backend: str = "auto",
        modifier: Optional[str] = None,
        fixed_max_results: Optional[int] = None,
        timelimit: Optional[Literal["d", "w", "m", "y"]] = None,
        region: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            enable_search=enable_search,
            enable_news=enable_news,
            backend=backend,
            modifier=modifier,
            fixed_max_results=fixed_max_results,
            timelimit=timelimit,
            region=region,
            **kwargs,
        )