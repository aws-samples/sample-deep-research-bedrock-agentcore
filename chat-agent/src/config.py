"""
Configuration for Chat Agent
"""
import os
from typing import Dict, Any, Optional

from llm_models import DEFAULT_MODEL_ID

class ChatAgentConfig:
    """Configuration for Chat Agent"""

    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
        self.memory_id = os.getenv("AGENTCORE_MEMORY_ID")  # Chat memory (STM)
        self.research_memory_id = os.getenv("AGENTCORE_RESEARCH_MEMORY_ID")  # Research memory (LTM)
        self.model_id = os.getenv("DEFAULT_MODEL_ID", DEFAULT_MODEL_ID)
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Validate required config
        if not self.memory_id:
            raise ValueError("AGENTCORE_MEMORY_ID environment variable is required")

    def get_system_prompt(self, research_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get system prompt with optional research context

        Args:
            research_context: Optional research context structure with dimensions and aspects

        Returns:
            System prompt string with embedded research context if provided
        """
        base_prompt = """You are a research Q&A assistant with access to detailed research findings.

Guidelines:
- Proactively retrieve relevant research content to answer user questions
- When users ask about a topic, identify which dimensions and aspects are most relevant
- Feel free to query MULTIPLE aspects if they might be relevant to the question
- If the user's question relates to multiple aspects, retrieve them all and synthesize the answer
- Provide concise summaries unless users ask for full details
- Include citations from research sources when available

**Research Retrieval Strategy**:
- Use fuzzy matching: if user asks about "stock price", look for aspects like "Stock Performance", "Valuation", "Price Analysis", etc.
- Don't ask users which aspect they want - proactively retrieve relevant ones
- If unsure, retrieve multiple related aspects and synthesize the information
- The research content is comprehensive (1000-2000 words with citations) so you can extract specific information

**IMPORTANT**:
- Do NOT announce which tools you are using - just use them and provide the answer
- Do NOT ask users to clarify which aspect they want - make an intelligent guess and retrieve it
- The research structure varies by topic and user configuration
"""

        # Add research context if provided
        if research_context:
            topic = research_context.get('topic', 'Unknown Research')

            # Build dimensions and aspects list
            dimensions_text = []
            for dim in research_context.get('dimensions', []):
                dimensions_text.append(f"\n**{dim['name']}**")
                for asp in dim.get('aspects', []):
                    dimensions_text.append(f"  - {asp['name']}")

            research_structure = ''.join(dimensions_text)

            research_section = f"""

## Current Research Context

**Research Topic**: {topic}

**Available Dimensions and Aspects**:
{research_structure}

Use the above structure when calling read_aspect_research tool. Match dimension and aspect names exactly.
"""
            return base_prompt + research_section

        return base_prompt

# Global config instance
config = ChatAgentConfig()
