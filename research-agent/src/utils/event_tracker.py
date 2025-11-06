"""Research Event Tracker for AgentCore Memory

Tracks high-level research workflow events in AgentCore Memory for:
- Workflow progress tracking
- Research analytics
- Event-based queries and filtering

Uses AgentCore Memory Events API (not checkpoints) for custom event storage.
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

# Initialize logger with explicit configuration
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ResearchEventTracker:
    """Tracks research workflow events in AgentCore Memory.

    This class provides a high-level event tracking system that:
    1. Logs key research milestones (start, aspect complete, research complete)
    2. Stores structured event data as blobs in AgentCore Memory
    3. Adds searchable metadata for filtering and querying
    4. Groups events by session_id for easy retrieval

    Unlike LangGraph checkpointer (low-level state snapshots), this stores
    human-readable research events optimized for analytics and monitoring.
    """

    def __init__(self, memory_id: str, region_name: str = "us-west-2", actor_id: Optional[str] = None):
        """Initialize event tracker.

        Args:
            memory_id: AgentCore Memory ID
            region_name: AWS region
            actor_id: Actor ID for all events (optional, can be set per-event)
        """
        self.memory_id = memory_id
        self.region_name = region_name
        self.actor_id = actor_id  # Can be None, set per-event instead
        self.client = boto3.client('bedrock-agentcore', region_name=region_name)

    def _create_event(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Dict[str, str]]] = None,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Create an event in AgentCore Memory.

        Args:
            session_id: Research session ID
            event_type: Type of event (research_start, aspect_complete, etc.)
            data: Event data (stored as blob)
            metadata: Searchable metadata (key -> {stringValue: value})
            actor_id: Actor ID for this event (overrides instance default)

        Returns:
            Event ID if successful, None otherwise
        """
        # Use provided actor_id or fall back to instance default
        final_actor_id = actor_id or self.actor_id

        # user_id must be provided - no silent fallback
        if not final_actor_id:
            raise ValueError("actor_id is required for event tracking - user_id not provided in workflow state")
        try:
            # Add event_type and timestamp to data
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **data
            }

            # Prepare metadata with event_type
            event_metadata = {
                'event_type': {'stringValue': event_type}
            }
            if metadata:
                event_metadata.update(metadata)

            # Serialize event_data to JSON string for blob storage
            blob_str = json.dumps(event_data, default=str)
            blob_size_kb = len(blob_str) / 1024

            # Log blob size for debugging
            logger.info(f"Creating event: {event_type}, blob size: {blob_size_kb:.2f} KB")

            # Check blob size limit (AgentCore Memory has 100KB limit per event)
            if blob_size_kb > 100:
                logger.warning(f"Blob size ({blob_size_kb:.2f} KB) exceeds 100KB limit, truncating content...")
                # Truncate content if too large
                # Keep metadata but truncate main content fields
                if 'research_content' in event_data and isinstance(event_data['research_content'], dict):
                    event_data['research_content']['main_content'] = f"[Content truncated - {blob_size_kb:.2f} KB]"
                    blob_str = json.dumps(event_data, default=str)
                    blob_size_kb = len(blob_str) / 1024
                    logger.info(f"After truncation: {blob_size_kb:.2f} KB")
                elif 'markdown_content' in event_data:
                    event_data['markdown_content'] = f"[Content truncated - {blob_size_kb:.2f} KB]"
                    blob_str = json.dumps(event_data, default=str)
                    blob_size_kb = len(blob_str) / 1024
                    logger.info(f"After truncation: {blob_size_kb:.2f} KB")

            # boto3 expects blob as JSON-serializable document
            response = self.client.create_event(
                memoryId=self.memory_id,
                actorId=final_actor_id,
                sessionId=session_id,
                eventTimestamp=datetime.now(timezone.utc),
                payload=[{
                    'blob': blob_str
                }],
                metadata=event_metadata
            )

            # Response structure: {'event': {'eventId': '...', ...}}
            event = response.get('event', {})
            event_id = event.get('eventId')

            if event_id:
                logger.info(f"✅ Created event: {event_type} -> {event_id}")
                logger.info(f"   Session ID: {session_id}")
                logger.info(f"   Actor ID: {final_actor_id}")
            else:
                logger.error(f"❌ No eventId in response. Response keys: {list(response.keys())}")
                if event:
                    logger.error(f"   Event keys: {list(event.keys())}")

            return event_id

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ ClientError creating event ({event_type}): [{error_code}] {error_msg}")
            logger.error(f"   Memory ID: {self.memory_id}")
            logger.error(f"   Session ID: {session_id}")
            logger.error(f"   Actor ID: {final_actor_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error creating event ({event_type}): {e}", exc_info=True)
            return None

    def log_research_start(
        self,
        session_id: str,
        topic: str,
        config: Dict[str, Any],
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log research workflow start event.

        Args:
            session_id: Research session ID
            topic: Research topic
            config: Research configuration (model, depth, type, etc.)
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'topic': topic,
            'model': config.get('llm_model', 'unknown'),
            'research_type': config.get('research_type', 'basic_web'),
            'research_depth': config.get('research_depth', 'balanced'),
            'research_context': config.get('research_context', ''),
            'has_references': bool(config.get('reference_materials'))
        }

        # Sanitize topic for metadata (regex: [a-zA-Z0-9\s._:/=+@-]*)
        metadata = {
            'topic': {'stringValue': self._sanitize_metadata_value(topic[:100])},
            'model': {'stringValue': config.get('llm_model', 'unknown')},
            'research_depth': {'stringValue': config.get('research_depth', 'balanced')}
        }

        event_id = self._create_event(session_id, 'research_start', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged research_start event: {event_id}")
        return event_id

    def log_references_prepared(
        self,
        session_id: str,
        reference_materials: list,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log reference materials preparation completion event.

        Args:
            session_id: Research session ID
            reference_materials: List of prepared reference materials with summaries
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'reference_materials': reference_materials,
            'reference_count': len(reference_materials),
            'total_key_points': sum(len(mat.get('key_points', [])) for mat in reference_materials)
        }

        metadata = {
            'reference_count': {'stringValue': str(len(reference_materials))}
        }

        event_id = self._create_event(session_id, 'references_prepared', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged references_prepared event: {event_id}")
        return event_id

    def log_dimensions_identified(
        self,
        session_id: str,
        dimensions: list,
        aspects_by_dimension: Dict[str, list],
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log dimensions and aspects identification event.

        Args:
            session_id: Research session ID
            dimensions: List of identified dimensions
            aspects_by_dimension: Aspects grouped by dimension
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'dimensions': dimensions,
            'dimension_count': len(dimensions),
            'aspects_by_dimension': aspects_by_dimension,
            'total_aspects': sum(len(aspects) for aspects in aspects_by_dimension.values())
        }

        metadata = {
            'dimension_count': {'stringValue': str(len(dimensions))},
            'total_aspects': {'stringValue': str(data['total_aspects'])}
        }

        event_id = self._create_event(session_id, 'dimensions_identified', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged dimensions_identified event: {event_id}")
        return event_id

    def _sanitize_metadata_value(self, value: str) -> str:
        """Sanitize string value for AgentCore Memory metadata.

        Metadata values must match pattern: [a-zA-Z0-9\\s._:/=+@-]*
        Replace disallowed characters with safe equivalents.
        """
        import re
        # Replace common special characters
        sanitized = value.replace('&', 'and')
        sanitized = sanitized.replace('(', '[')
        sanitized = sanitized.replace(')', ']')
        sanitized = sanitized.replace(',', '')
        # Remove any remaining disallowed characters
        sanitized = re.sub(r'[^a-zA-Z0-9\s._:/=+@-]', '', sanitized)
        return sanitized

    def log_aspect_research_complete(
        self,
        session_id: str,
        dimension: str,
        aspect: str,
        research_content: Dict[str, Any],
        citations_count: int = 0,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log aspect research completion event with FULL content.

        Args:
            session_id: Research session ID
            dimension: Dimension name
            aspect: Aspect name
            research_content: FULL structured research result (entire dict)
            citations_count: Number of citations found
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        # Store FULL research content in blob (original names)
        data = {
            'dimension': dimension,
            'aspect': aspect,
            'research_content': research_content,  # Full content!
            'citations_count': citations_count,
            'word_count': research_content.get('word_count', 0),
            'content_size_bytes': len(str(research_content))
        }

        # Metadata uses sanitized values (special characters replaced)
        metadata = {
            'dimension': {'stringValue': self._sanitize_metadata_value(dimension[:100])},
            'aspect': {'stringValue': self._sanitize_metadata_value(aspect[:100])},
            'citations_count': {'stringValue': str(citations_count)},
            'word_count': {'stringValue': str(research_content.get('word_count', 0))}
        }

        event_id = self._create_event(session_id, 'aspect_research_complete', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged aspect_research_complete event: {event_id} ({dimension} / {aspect})")
        return event_id

    def log_dimension_document_complete(
        self,
        session_id: str,
        dimension: str,
        markdown_content: str,
        word_count: int,
        filename: str,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log dimension document generation completion event with FULL content.

        Args:
            session_id: Research session ID
            dimension: Dimension name
            markdown_content: FULL markdown content of the document
            word_count: Word count of generated document
            filename: Document filename
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'dimension': dimension,
            'markdown_content': markdown_content,  # Full markdown!
            'word_count': word_count,
            'filename': filename,
            'content_size_bytes': len(markdown_content)
        }

        # Metadata uses sanitized dimension name
        metadata = {
            'dimension': {'stringValue': self._sanitize_metadata_value(dimension[:100])},
            'word_count': {'stringValue': str(word_count)}
        }

        event_id = self._create_event(session_id, 'dimension_document_complete', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged dimension_document_complete event: {event_id} ({dimension})")
        return event_id

    def log_research_complete(
        self,
        session_id: str,
        dimensions: list,
        total_aspects: int,
        elapsed_time: float,
        output_files: Dict[str, str],
        s3_uploads: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log research workflow completion event.

        Args:
            session_id: Research session ID
            dimensions: List of dimensions researched
            total_aspects: Total number of aspects researched
            elapsed_time: Total elapsed time in seconds
            output_files: Generated output files (docx, md)
            s3_uploads: S3 upload information
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'dimensions': dimensions,
            'dimension_count': len(dimensions),
            'total_aspects': total_aspects,
            'elapsed_time_seconds': elapsed_time,
            'output_files': output_files,
            's3_uploads': s3_uploads or {}
        }

        metadata = {
            'dimension_count': {'stringValue': str(len(dimensions))},
            'total_aspects': {'stringValue': str(total_aspects)},
            'elapsed_time': {'stringValue': f"{elapsed_time:.2f}"}
        }

        event_id = self._create_event(session_id, 'research_complete', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged research_complete event: {event_id}")
        return event_id

    def log_error(
        self,
        session_id: str,
        error_type: str,
        error_message: str,
        node_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None
    ) -> Optional[str]:
        """Log error event.

        Args:
            session_id: Research session ID
            error_type: Type of error
            error_message: Error message
            node_name: Node where error occurred
            context: Additional error context
            actor_id: Actor ID for this event (optional)

        Returns:
            Event ID if successful
        """
        data = {
            'error_type': error_type,
            'error_message': error_message[:500],  # Truncate
            'node_name': node_name,
            'context': context or {}
        }

        metadata = {
            'error_type': {'stringValue': error_type[:100]},
            'node_name': {'stringValue': node_name[:100] if node_name else 'unknown'}
        }

        event_id = self._create_event(session_id, 'error', data, metadata, actor_id=actor_id)
        if event_id:
            logger.info(f"📝 Logged error event: {event_id}")
        return event_id


# Singleton instance
_event_tracker = None


def get_event_tracker(memory_id: Optional[str] = None, region_name: Optional[str] = None) -> Optional[ResearchEventTracker]:
    """Get or create singleton event tracker instance.

    Args:
        memory_id: AgentCore Memory ID (required on first call)
        region_name: AWS region (optional)

    Returns:
        ResearchEventTracker instance or None if not configured
    """
    global _event_tracker

    if _event_tracker is None:
        from src.config.memory_config import get_memory_id_from_config, get_region, is_agentcore_enabled

        if not is_agentcore_enabled():
            return None

        final_memory_id = memory_id or get_memory_id_from_config()
        final_region = region_name or get_region()

        if not final_memory_id:
            logger.warning("⚠️  Event tracker disabled: No memory_id configured")
            return None

        _event_tracker = ResearchEventTracker(final_memory_id, final_region)
        logger.info(f"📝 Event tracker initialized (Memory: {final_memory_id})")

    return _event_tracker
