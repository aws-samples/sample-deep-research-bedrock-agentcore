"""Research configuration for tool selection and research settings"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum


class ResearchToolType(str, Enum):
    """Available research tool types"""
    ARXIV_SEARCH = "arxiv_search"
    ARXIV_GET_PAPER = "arxiv_get_paper"
    DDG_SEARCH = "ddg_search"
    DDG_NEWS = "ddg_news"
    TAVILY_SEARCH = "tavily_search"
    TAVILY_EXTRACT = "tavily_extract"
    GOOGLE_WEB_SEARCH = "google_web_search"
    GOOGLE_IMAGE_SEARCH = "google_image_search"
    WIKIPEDIA_SEARCH = "wikipedia_search"
    WIKIPEDIA_GET_ARTICLE = "wikipedia_get_article"
    # Finance tools - match Gateway tool names
    STOCK_QUOTE = "stock_quote"
    STOCK_HISTORY = "stock_history"
    FINANCIAL_NEWS = "financial_news"
    STOCK_ANALYSIS = "stock_analysis"


# Research depth configurations (unified)
DEPTH_CONFIGS = {
    "quick": {
        "dimensions": 2,
        "aspects_per_dimension": 2,
        "arxiv_max_results": 3,
        "web_search_max_results": 3,
        "agent_max_iterations": 15,  # Limit agent tool call cycles
        "description": "Quick overview with 2×2 structure"
    },
    "balanced": {
        "dimensions": 3,
        "aspects_per_dimension": 3,
        "arxiv_max_results": 5,
        "web_search_max_results": 5,
        "agent_max_iterations": 25,  # Balanced iteration limit
        "description": "Balanced coverage with 3×3 structure"
    },
    "deep": {
        "dimensions": 5,
        "aspects_per_dimension": 3,
        "arxiv_max_results": 5,
        "web_search_max_results": 5,
        "agent_max_iterations": 35,  # More iterations for deep research
        "description": "Comprehensive analysis with 5×3 structure"
    }
}

# ============================================================================
# Concurrency Control Settings
# ============================================================================
# Controls maximum parallel executions for specific node types
# Uses asyncio.Semaphore to limit concurrent API calls and resource usage

CONCURRENCY_LIMITS = {
    "research": 1,  # Sequential research execution (Gateway MCP session concurrency issue)
    "dimension_reduction": 1,  # Sequential dimension synthesis (one at a time)
    "aspect_analysis": None,  # Unlimited (fast, no heavy API calls)
}

# Global default for nodes not specified above
DEFAULT_CONCURRENCY_LIMIT = 5


class ResearchConfig:
    """
    Configuration for research stage tools and settings.

    Tools are automatically selected based on research_type using tool_mappings.py.
    This is the single source of truth for tool configuration.
    """

    def __init__(
        self,
        research_type: str,  # REQUIRED: "basic_web", "advanced_web", "academic", "financial", "comprehensive"
        research_depth: str = "balanced",  # "quick", "balanced", "deep"
        llm_model: str = "nova_pro",  # "nova_pro" or "sonnet45"
        max_paper_content_chars: int = 10000,
        # Optional overrides for custom configurations
        arxiv_max_results: Optional[int] = None,
        web_search_max_results: Optional[int] = None,
        target_dimensions: Optional[int] = None,
        target_aspects_per_dimension: Optional[int] = None,
        agent_max_iterations: Optional[int] = None
    ):
        """
        Initialize research configuration.

        Args:
            research_type: Type of research (REQUIRED) - one of: "basic_web", "advanced_web", "academic", "financial", "comprehensive"
                          Tools are automatically selected from tool_mappings.py based on this value
            research_depth: Research depth level ("quick", "balanced", "deep")
                - quick: 2 dimensions × 2 aspects, 3 results per search
                - balanced: 3 dimensions × 3 aspects, 5 results per search (default)
                - deep: 5 dimensions × 3 aspects, 7-10 results per search
            llm_model: LLM model to use ("nova_pro", "claude_haiku", "claude_sonnet")
            max_paper_content_chars: Max characters to extract from papers
            arxiv_max_results: Override default for depth (optional)
            web_search_max_results: Override default for depth (optional)
            target_dimensions: Override default for depth (optional)
            target_aspects_per_dimension: Override default for depth (optional)
            agent_max_iterations: Override default for depth (optional)

        Note: Tools are loaded dynamically from tool_mappings.py based on research_type.
              See src/catalog/tool_mappings.py for the full list of available tools per type.
        """
        # Validate research_type
        valid_types = ["basic_web", "advanced_web", "academic", "financial", "comprehensive", "custom"]
        if research_type not in valid_types:
            raise ValueError(f"Invalid research_type: {research_type}. Must be one of {valid_types}")

        # Get depth configuration
        if research_depth not in DEPTH_CONFIGS:
            raise ValueError(f"Invalid research_depth: {research_depth}. Must be one of {list(DEPTH_CONFIGS.keys())}")

        depth_config = DEPTH_CONFIGS[research_depth]

        # Apply depth settings with optional overrides
        self.research_type = research_type
        self.research_depth = research_depth
        self.llm_model = llm_model
        self.target_dimensions = target_dimensions if target_dimensions is not None else depth_config["dimensions"]
        self.target_aspects_per_dimension = target_aspects_per_dimension if target_aspects_per_dimension is not None else depth_config["aspects_per_dimension"]
        self.arxiv_max_results = arxiv_max_results if arxiv_max_results is not None else depth_config["arxiv_max_results"]
        self.web_search_max_results = web_search_max_results if web_search_max_results is not None else depth_config["web_search_max_results"]
        self.agent_max_iterations = agent_max_iterations if agent_max_iterations is not None else depth_config["agent_max_iterations"]
        self.max_paper_content_chars = max_paper_content_chars

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for state storage"""
        return {
            "research_type": self.research_type,
            "research_depth": self.research_depth,
            "llm_model": self.llm_model,
            "target_dimensions": self.target_dimensions,
            "target_aspects_per_dimension": self.target_aspects_per_dimension,
            "arxiv_max_results": self.arxiv_max_results,
            "web_search_max_results": self.web_search_max_results,
            "agent_max_iterations": self.agent_max_iterations,
            "max_paper_content_chars": self.max_paper_content_chars
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchConfig":
        """
        Create config from dictionary.

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if "research_type" not in data:
            raise ValueError("research_type is required in config dict")

        research_type = data["research_type"]
        valid_types = ["basic_web", "advanced_web", "academic", "financial", "comprehensive", "custom"]
        if research_type not in valid_types:
            raise ValueError(f"Invalid research_type: {research_type}. Must be one of {valid_types}")

        return cls(
            research_type=research_type,
            research_depth=data.get("research_depth", "balanced"),
            llm_model=data.get("llm_model", "nova_pro"),
            max_paper_content_chars=data.get("max_paper_content_chars", 50000),
            arxiv_max_results=data.get("arxiv_max_results"),
            web_search_max_results=data.get("web_search_max_results"),
            target_dimensions=data.get("target_dimensions"),
            target_aspects_per_dimension=data.get("target_aspects_per_dimension"),
            agent_max_iterations=data.get("agent_max_iterations")
        )

    def get_system_prompt_addition(self) -> str:
        """Get additional system prompt text based on research type and depth"""
        depth_config = DEPTH_CONFIGS.get(self.research_depth, DEPTH_CONFIGS["balanced"])

        depth_instructions = {
            "quick": "Focus on finding 2-3 key sources quickly.",
            "balanced": "Find 3-5 relevant sources and synthesize key findings.",
            "deep": "Conduct thorough research with 5-10 sources, including detailed analysis."
        }

        # Research type specific tool guidance
        type_guidance = {
            "financial": """
FINANCIAL RESEARCH TOOLS:
You have specialized financial tools that provide structured, real-time stock data:

• stock_quote - Current price, market cap, P/E ratio, volume
• stock_analysis - Valuation metrics, financial metrics, analyst recommendations
• stock_history - Historical price data over time periods
• financial_news - Latest news and developments

These tools are optimized for stock-specific queries and provide more accurate data than general web search.
For broader market context or industry trends, web search tools may be more appropriate.
""",
            "academic": """
ACADEMIC RESEARCH TOOLS:
• arxiv_search - Search for scientific papers
• arxiv_get_paper - Retrieve full paper content by ID
• wikipedia_search - Encyclopedic information

These tools are optimized for academic and scientific topics.
""",
            "basic_web": """
WEB RESEARCH TOOLS:
• ddg_search, google_web_search - General web search
• tavily_search - AI-powered web search with relevance scores
• wikipedia_search - Encyclopedic information

These tools provide broad coverage across diverse topics.
"""
        }

        type_prompt = type_guidance.get(self.research_type, "")

        return f"""
RESEARCH CONFIGURATION: {self.research_depth.upper()}
{depth_config["description"]}
{depth_instructions.get(self.research_depth, depth_instructions["balanced"])}
{type_prompt}
"""


# Predefined configurations for common scenarios (lazy-initialized)
_RESEARCH_CONFIGS = None


def _get_research_configs() -> Dict[str, ResearchConfig]:
    """Lazy initialization of research configs"""
    global _RESEARCH_CONFIGS
    if _RESEARCH_CONFIGS is None:
        _RESEARCH_CONFIGS = {
            "academic": ResearchConfig(
                research_type="academic",
                research_depth="deep"
            ),

            "basic_web": ResearchConfig(
                research_type="basic_web",
                research_depth="balanced"
            ),

            "advanced_web": ResearchConfig(
                research_type="advanced_web",
                research_depth="deep"
            ),

            "financial": ResearchConfig(
                research_type="financial",
                research_depth="balanced"
            ),

            "comprehensive": ResearchConfig(
                research_type="comprehensive",
                research_depth="deep"
            ),
        }
    return _RESEARCH_CONFIGS


def get_research_config(config_name: str = "comprehensive") -> ResearchConfig:
    """
    Get a predefined research configuration.

    Args:
        config_name: Name of the configuration
            - "academic": Academic papers with Wikipedia
            - "basic_web": DuckDuckGo web search with Wikipedia
            - "advanced_web": Tavily + Google search with Wikipedia (requires API keys)
            - "financial": Financial market data with basic web search
            - "comprehensive": Academic + web + Wikipedia + Google (default)

    Returns:
        ResearchConfig instance
    """
    configs = _get_research_configs()
    return configs.get(config_name, configs["comprehensive"])


def create_custom_config(
    research_type: str = "basic_web",
    depth: str = "balanced"
) -> ResearchConfig:
    """
    Create a custom research configuration.

    Args:
        research_type: Type of research ("basic_web", "advanced_web", "academic", "financial", "comprehensive")
        depth: Research depth ("quick", "balanced", "deep")

    Returns:
        Custom ResearchConfig instance

    Note: Tools are automatically selected from tool_mappings.py based on research_type
    """
    return ResearchConfig(
        research_type=research_type,
        research_depth=depth
    )
