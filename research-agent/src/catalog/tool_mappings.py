"""
Tool mappings for research types
Defines which tools are available for each research type and provides reverse lookups
"""
from enum import Enum
from typing import List, Set, Dict
from dataclasses import dataclass


class ResearchType(Enum):
    """Research types matching frontend RESEARCH_TYPES"""
    BASIC_WEB = "basic_web"
    ADVANCED_WEB = "advanced_web"
    ACADEMIC = "academic"
    FINANCIAL = "financial"
    COMPREHENSIVE = "comprehensive"
    CUSTOM = "custom"


class ToolCategory(Enum):
    """Tool categories for organization"""
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    ACADEMIC = "academic"
    FINANCE = "finance"
    UTILITY = "utility"
    LOCAL = "local"


# ============================================================================
# Gateway Tool Categories (for auto-discovery)
# ============================================================================

GATEWAY_TOOL_CATEGORIES: Dict[str, str] = {
    # Search tools
    "ddg_search": ToolCategory.SEARCH.value,
    "ddg_news": ToolCategory.SEARCH.value,
    "google_web_search": ToolCategory.SEARCH.value,
    "google_image_search": ToolCategory.SEARCH.value,
    "tavily_search": ToolCategory.SEARCH.value,
    "tavily_extract": ToolCategory.SEARCH.value,

    # Knowledge base tools
    "wikipedia_search": ToolCategory.KNOWLEDGE.value,
    "wikipedia_get_article": ToolCategory.KNOWLEDGE.value,

    # Academic tools
    "arxiv_search": ToolCategory.ACADEMIC.value,
    "arxiv_get_paper": ToolCategory.ACADEMIC.value,

    # Financial tools
    "stock_quote": ToolCategory.FINANCE.value,
    "stock_history": ToolCategory.FINANCE.value,
    "financial_news": ToolCategory.FINANCE.value,
    "stock_analysis": ToolCategory.FINANCE.value,
}


# ============================================================================
# Research Type → Tools Mapping (Forward Mapping)
# ============================================================================

RESEARCH_TYPE_TOOLS: Dict[str, List[str]] = {
    # Basic Web: Essential web search + Wikipedia
    ResearchType.BASIC_WEB.value: [
        "ddg_search",
        "google_web_search",
        "tavily_search",
        "tavily_extract",
        "wikipedia_search",
        "wikipedia_get_article",
    ],

    # Advanced Web: All web tools + news + images
    ResearchType.ADVANCED_WEB.value: [
        "ddg_search",
        "ddg_news",
        "google_web_search",
        "google_image_search",
        "tavily_search",
        "tavily_extract",
        "wikipedia_search",
        "wikipedia_get_article",
    ],

    # Academic: Web search + ArXiv + Wikipedia
    ResearchType.ACADEMIC.value: [
        "ddg_search",
        "google_web_search",
        "tavily_search",
        "tavily_extract",
        "arxiv_search",
        "arxiv_get_paper",
        "wikipedia_search",
        "wikipedia_get_article",
    ],

    # Financial: Focus on financial tools with minimal web search
    ResearchType.FINANCIAL.value: [
        "stock_quote",
        "stock_history",
        "financial_news",
        "stock_analysis",
        "ddg_search",  # For general company/market info
        "ddg_news",    # For recent financial news
    ],

    # Comprehensive: All search, knowledge, and academic tools (excluding finance)
    ResearchType.COMPREHENSIVE.value: [
        # Search
        "ddg_search",
        "ddg_news",
        "google_web_search",
        "google_image_search",
        "tavily_search",
        "tavily_extract",
        # Knowledge
        "wikipedia_search",
        "wikipedia_get_article",
        # Academic
        "arxiv_search",
        "arxiv_get_paper",
    ],

    # Custom: Empty by default (user will configure)
    ResearchType.CUSTOM.value: [],
}


# ============================================================================
# Tool → Research Types Mapping (Reverse Mapping)
# ============================================================================

def build_reverse_mapping() -> Dict[str, Set[str]]:
    """
    Build reverse mapping: tool_name → set of research_types
    Automatically generated from RESEARCH_TYPE_TOOLS
    """
    reverse_map: Dict[str, Set[str]] = {}

    for research_type, tools in RESEARCH_TYPE_TOOLS.items():
        for tool_name in tools:
            if tool_name not in reverse_map:
                reverse_map[tool_name] = set()
            reverse_map[tool_name].add(research_type)

    return reverse_map


# Build reverse mapping at module load time
TOOL_TO_RESEARCH_TYPES: Dict[str, Set[str]] = build_reverse_mapping()


# ============================================================================
# Category-based Lookups
# ============================================================================

def get_tools_by_category(category: ToolCategory) -> List[str]:
    """Get all tools in a specific category"""
    return [
        tool_name
        for tool_name, tool_category in GATEWAY_TOOL_CATEGORIES.items()
        if tool_category == category.value
    ]


def get_tools_by_research_type(research_type: str) -> List[str]:
    """
    Get tools for a specific research type

    Args:
        research_type: One of ResearchType values (e.g., 'basic_web', 'academic')

    Returns:
        List of tool names available for this research type
    """
    return RESEARCH_TYPE_TOOLS.get(research_type, [])


def get_research_types_for_tool(tool_name: str) -> Set[str]:
    """
    Get research types that use a specific tool (reverse lookup)

    Args:
        tool_name: Name of the tool (e.g., 'arxiv_search')

    Returns:
        Set of research types that use this tool
    """
    return TOOL_TO_RESEARCH_TYPES.get(tool_name, set())


def is_tool_available_for_research_type(tool_name: str, research_type: str) -> bool:
    """
    Check if a tool is available for a specific research type

    Args:
        tool_name: Name of the tool
        research_type: Research type to check

    Returns:
        True if tool is available for this research type
    """
    return research_type in get_research_types_for_tool(tool_name)


# ============================================================================
# Tool Metadata
# ============================================================================

@dataclass
class ToolInfo:
    """Extended tool information"""
    name: str
    category: str
    research_types: Set[str]
    description: str = ""
    priority: int = 0  # Higher priority = preferred tool


# Priority mapping for tools (when multiple tools can do similar things)
TOOL_PRIORITIES = {
    # Search priorities (Tavily > Google > DuckDuckGo for quality)
    "tavily_search": 100,
    "google_web_search": 90,
    "ddg_search": 80,

    # Knowledge priorities
    "wikipedia_search": 100,

    # Academic priorities
    "arxiv_search": 100,

    # Finance priorities
    "stock_quote": 100,
    "financial_news": 90,
}


def get_tool_info(tool_name: str) -> ToolInfo:
    """
    Get comprehensive information about a tool

    Args:
        tool_name: Name of the tool

    Returns:
        ToolInfo object with all metadata
    """
    return ToolInfo(
        name=tool_name,
        category=GATEWAY_TOOL_CATEGORIES.get(tool_name, ToolCategory.UTILITY.value),
        research_types=get_research_types_for_tool(tool_name),
        priority=TOOL_PRIORITIES.get(tool_name, 50)
    )


def get_preferred_tools_for_category(
    research_type: str,
    category: ToolCategory,
    max_tools: int = None
) -> List[str]:
    """
    Get preferred tools for a research type and category, sorted by priority

    Args:
        research_type: Research type
        category: Tool category to filter by
        max_tools: Maximum number of tools to return (None = all)

    Returns:
        List of tool names sorted by priority
    """
    # Get all tools for this research type
    available_tools = get_tools_by_research_type(research_type)

    # Filter by category and sort by priority
    category_tools = [
        tool_name
        for tool_name in available_tools
        if GATEWAY_TOOL_CATEGORIES.get(tool_name) == category.value
    ]

    # Sort by priority (descending)
    sorted_tools = sorted(
        category_tools,
        key=lambda t: TOOL_PRIORITIES.get(t, 50),
        reverse=True
    )

    if max_tools:
        return sorted_tools[:max_tools]
    return sorted_tools


# ============================================================================
# Validation and Debugging
# ============================================================================

def validate_mappings() -> List[str]:
    """
    Validate tool mappings for consistency
    Returns list of warnings/errors
    """
    issues = []

    # Check for tools without categories
    all_tools = set()
    for tools in RESEARCH_TYPE_TOOLS.values():
        all_tools.update(tools)

    for tool_name in all_tools:
        if tool_name not in GATEWAY_TOOL_CATEGORIES:
            issues.append(f"⚠️  Tool '{tool_name}' has no category defined")

    # Check for orphaned categories
    for tool_name in GATEWAY_TOOL_CATEGORIES:
        if tool_name not in TOOL_TO_RESEARCH_TYPES:
            issues.append(f"⚠️  Tool '{tool_name}' is not used by any research type")

    return issues


def print_mapping_summary():
    """Print summary of tool mappings for debugging"""
    print("=" * 80)
    print("TOOL MAPPINGS SUMMARY")
    print("=" * 80)

    # Research types
    print("\n📋 Research Types → Tools:")
    for research_type, tools in RESEARCH_TYPE_TOOLS.items():
        print(f"\n  {research_type}: ({len(tools)} tools)")
        for tool in sorted(tools):
            category = GATEWAY_TOOL_CATEGORIES.get(tool, "unknown")
            print(f"    - {tool} [{category}]")

    # Reverse mapping
    print("\n🔄 Tools → Research Types (Reverse):")
    for tool_name in sorted(TOOL_TO_RESEARCH_TYPES.keys()):
        types = TOOL_TO_RESEARCH_TYPES[tool_name]
        print(f"  {tool_name}: {', '.join(sorted(types))}")

    # Categories
    print("\n📂 Tools by Category:")
    for category in ToolCategory:
        tools = get_tools_by_category(category)
        if tools:
            print(f"  {category.value}: {', '.join(sorted(tools))}")

    # Validation
    print("\n✅ Validation:")
    issues = validate_mappings()
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  All mappings valid!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run validation and print summary when executed directly
    print_mapping_summary()
