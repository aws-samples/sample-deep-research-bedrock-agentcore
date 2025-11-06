"""
Tool Catalog for unified tool management
- Discovery from Gateway and local sources
- Registration and metadata
- Tool lookup and filtering
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolSource(Enum):
    """Tool source types"""
    GATEWAY = "gateway"      # From AgentCore Gateway via MCP
    LOCAL = "local"          # Local Python tools
    BUILTIN = "builtin"      # Built-in LangChain tools


@dataclass
class ToolMetadata:
    """Tool metadata and registration info"""
    name: str
    description: str
    source: ToolSource
    category: str  # search, knowledge, finance, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict] = field(default_factory=list)
    enabled: bool = True
    version: str = "1.0"
    gateway_name: Optional[str] = None  # Original Gateway tool name if different
    research_types: List[str] = field(default_factory=list)  # Which research types use this


class ToolCatalog:
    """
    Central registry for all available tools
    Supports discovery, registration, and lookup
    """

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_source: Dict[ToolSource, List[str]] = {}
        self._by_research_type: Dict[str, List[str]] = {}
        logger.info("Tool Catalog initialized")

    def register(self, tool_meta: ToolMetadata):
        """Register a tool in the catalog"""
        self._tools[tool_meta.name] = tool_meta

        # Index by category
        if tool_meta.category not in self._by_category:
            self._by_category[tool_meta.category] = []
        if tool_meta.name not in self._by_category[tool_meta.category]:
            self._by_category[tool_meta.category].append(tool_meta.name)

        # Index by source
        if tool_meta.source not in self._by_source:
            self._by_source[tool_meta.source] = []
        if tool_meta.name not in self._by_source[tool_meta.source]:
            self._by_source[tool_meta.source].append(tool_meta.name)

        # Index by research type
        for research_type in tool_meta.research_types:
            if research_type not in self._by_research_type:
                self._by_research_type[research_type] = []
            if tool_meta.name not in self._by_research_type[research_type]:
                self._by_research_type[research_type].append(tool_meta.name)

        logger.info(f"✅ Registered: {tool_meta.name} ({tool_meta.source.value}, {tool_meta.category})")

    def unregister(self, name: str):
        """Unregister a tool from the catalog"""
        if name in self._tools:
            tool_meta = self._tools[name]

            # Remove from indexes
            if tool_meta.category in self._by_category:
                self._by_category[tool_meta.category].remove(name)

            if tool_meta.source in self._by_source:
                self._by_source[tool_meta.source].remove(name)

            for research_type in tool_meta.research_types:
                if research_type in self._by_research_type:
                    self._by_research_type[research_type].remove(name)

            # Remove tool
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")

    def get(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name"""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if tool exists in catalog"""
        return name in self._tools

    def list_all(self) -> List[ToolMetadata]:
        """List all registered tools"""
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """List all tool names"""
        return list(self._tools.keys())

    def list_by_category(self, category: str) -> List[ToolMetadata]:
        """List tools in a specific category"""
        tool_names = self._by_category.get(category, [])
        return [self._tools[name] for name in tool_names]

    def list_by_source(self, source: ToolSource) -> List[ToolMetadata]:
        """List tools from a specific source"""
        tool_names = self._by_source.get(source, [])
        return [self._tools[name] for name in tool_names]

    def list_by_research_type(self, research_type: str) -> List[ToolMetadata]:
        """List tools available for a specific research type"""
        tool_names = self._by_research_type.get(research_type, [])
        return [self._tools[name] for name in tool_names]

    async def discover_gateway_tools(self, session):
        """
        Auto-discover tools from Gateway
        Maps Gateway tools to catalog entries with research type mappings

        Args:
            session: MCP ClientSession instance

        Returns:
            List of discovered ToolMetadata objects
        """
        from src.catalog.tool_discovery import discover_from_gateway
        tools = await discover_from_gateway(session)

        for tool in tools:
            self.register(tool)

        logger.info(f"📦 Discovered {len(tools)} Gateway tools")
        return tools

    def register_local_tools(self, tools: List[Any]):
        """
        Register local Python tools

        Args:
            tools: List of tool objects (LangChain tools or callable)
        """
        from src.catalog.tool_discovery import discover_from_local
        tool_metas = discover_from_local(tools)

        for tool_meta in tool_metas:
            self.register(tool_meta)

        logger.info(f"📦 Registered {len(tool_metas)} local tools")

    def filter_tools(
        self,
        category: Optional[str] = None,
        source: Optional[ToolSource] = None,
        research_type: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[ToolMetadata]:
        """
        Filter tools by multiple criteria

        Args:
            category: Filter by category
            source: Filter by source
            research_type: Filter by research type
            enabled_only: Only return enabled tools

        Returns:
            Filtered list of ToolMetadata
        """
        tools = self.list_all()

        if category:
            tools = [t for t in tools if t.category == category]

        if source:
            tools = [t for t in tools if t.source == source]

        if research_type:
            tools = [t for t in tools if research_type in t.research_types]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return tools

    def get_stats(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        return {
            "total_tools": len(self._tools),
            "by_source": {
                source.value: len(tool_names)
                for source, tool_names in self._by_source.items()
            },
            "by_category": {
                category: len(tool_names)
                for category, tool_names in self._by_category.items()
            },
            "by_research_type": {
                research_type: len(tool_names)
                for research_type, tool_names in self._by_research_type.items()
            }
        }

    def print_summary(self):
        """Print catalog summary"""
        stats = self.get_stats()

        print("=" * 80)
        print("TOOL CATALOG SUMMARY")
        print("=" * 80)
        print(f"\n📊 Total Tools: {stats['total_tools']}")

        print("\n📂 By Source:")
        for source, count in stats['by_source'].items():
            print(f"   {source}: {count}")

        print("\n🏷️  By Category:")
        for category, count in stats['by_category'].items():
            print(f"   {category}: {count}")

        print("\n🔬 By Research Type:")
        for research_type, count in stats['by_research_type'].items():
            print(f"   {research_type}: {count}")

        print("\n" + "=" * 80)


# ============================================================================
# Global Catalog Instance
# ============================================================================

_catalog: Optional[ToolCatalog] = None


def get_catalog() -> ToolCatalog:
    """
    Get global tool catalog instance
    Creates on first access
    """
    global _catalog
    if _catalog is None:
        _catalog = ToolCatalog()
    return _catalog


def reset_catalog():
    """Reset global catalog (useful for testing)"""
    global _catalog
    _catalog = None
