"""DynamoDB status updater for research workflow

Thread-safe status updates for parallel node execution.
Handles concurrent updates from multiple dimensions/aspects running in parallel.
"""

import os
import boto3
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict


class ResearchStatusUpdater:
    """Thread-safe DynamoDB status updater for research workflow

    Handles concurrent updates from parallel nodes (aspect_analysis, research, dimension_reduction)
    using locks to prevent race conditions during DynamoDB updates.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.table_name = os.getenv('DYNAMODB_STATUS_TABLE')

        # Thread safety for parallel execution
        self._lock = threading.Lock()

        # Accumulate parallel results before batch update
        self._pending_dimensions = set()
        self._pending_aspects = defaultdict(list)  # {dimension: [aspects]}
        self._pending_research = {}  # {aspect_key: research_data}
        self._pending_dimension_docs = {}  # {dimension: doc_path}

        if not self.table_name:
            print("⚠️  DYNAMODB_STATUS_TABLE not set, status updates disabled")
            self.enabled = False
            return

        try:
            # Get region from environment (set by AgentCore Runtime)
            region = os.getenv('AWS_REGION', 'us-west-2')
            self.ddb = boto3.resource('dynamodb', region_name=region)
            self.table = self.ddb.Table(self.table_name)
            self.enabled = True
            print(f"✅ Status updater initialized for session: {session_id}")
        except Exception as e:
            print(f"⚠️  Failed to initialize DynamoDB client: {e}")
            self.enabled = False

    def _update_ddb(self, **kwargs):
        """Internal method to perform DynamoDB update (called within lock)"""
        if not self.enabled:
            return

        try:
            from decimal import Decimal

            # Build update expression
            update_expr = ['#updated_at = :updated_at']
            expr_names = {'#updated_at': 'updated_at'}
            expr_values = {':updated_at': datetime.now(timezone.utc).isoformat()}

            for key, value in kwargs.items():
                update_expr.append(f'#{key} = :{key}')
                expr_names[f'#{key}'] = key
                # Convert float to Decimal for DynamoDB
                if isinstance(value, float):
                    expr_values[f':{key}'] = Decimal(str(value))
                else:
                    expr_values[f':{key}'] = value

            self.table.update_item(
                Key={'session_id': self.session_id},
                UpdateExpression='SET ' + ', '.join(update_expr),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )

            # Only log key fields to avoid clutter
            log_keys = [k for k in kwargs.keys() if k in ['current_stage', 'status', 'dimension_count', 'total_aspects']]
            if log_keys:
                print(f"✅ Status updated: {log_keys}")

        except Exception as e:
            print(f"⚠️  Failed to update DynamoDB status: {e}")

    def update(self, **kwargs):
        """Update research status in DynamoDB (thread-safe)"""
        with self._lock:
            self._update_ddb(**kwargs)

    def update_stage(self, stage: str, **additional):
        """Update current stage with optional additional fields"""
        self.update(current_stage=stage, **additional)

    def update_progress(self, **progress):
        """Update progress fields (dimensions, aspects, etc.)"""
        self.update(**progress)

    # ========== Parallel-safe methods for aggregating results ==========

    def add_dimension(self, dimension: str):
        """Add a dimension (called from parallel aspect_analysis nodes)"""
        with self._lock:
            self._pending_dimensions.add(dimension)

    def add_aspect(self, dimension: str, aspect: Dict[str, Any]):
        """Add an aspect to a dimension (called from parallel aspect_analysis nodes)"""
        with self._lock:
            self._pending_aspects[dimension].append(aspect)

    def flush_dimensions_and_aspects(self):
        """Flush accumulated dimensions and aspects to DynamoDB (called after barrier)"""
        with self._lock:
            if not self._pending_dimensions:
                return

            dimensions_list = sorted(list(self._pending_dimensions))
            aspects_by_dimension = dict(self._pending_aspects)

            total_aspects = sum(len(aspects) for aspects in aspects_by_dimension.values())

            self._update_ddb(
                dimensions=dimensions_list,
                dimension_count=len(dimensions_list),
                aspects_by_dimension=aspects_by_dimension,
                total_aspects=total_aspects
            )

            print(f"📊 Flushed: {len(dimensions_list)} dimensions, {total_aspects} aspects")

    def add_research_result(self, dimension: str, aspect_name: str, research_data: Dict[str, Any]):
        """Add research result (called from parallel research nodes)"""
        with self._lock:
            aspect_key = f"{dimension}::{aspect_name}"
            self._pending_research[aspect_key] = research_data

    def flush_research_results(self):
        """Flush accumulated research results to DynamoDB (called after research barrier)"""
        with self._lock:
            if not self._pending_research:
                return

            # Store ONLY metadata (not full content)
            # Full content is stored in AgentCore Memory
            # Frontend only needs: word_count and sources_count
            research_metadata = {
                key: {
                    'word_count': data.get('word_count', 0),
                    'sources_count': len(data.get('key_sources', [])) if 'key_sources' in data else 0
                }
                for key, data in self._pending_research.items()
            }

            self._update_ddb(
                research_by_aspect=research_metadata,
                research_completed_count=len(self._pending_research)
            )

            print(f"🔬 Flushed: {len(self._pending_research)} research results")
            print(f"   Sample: {list(research_metadata.keys())[:2]}")

    def add_dimension_document(self, dimension: str, doc_path: str):
        """Add dimension document path (called from parallel dimension_reduction nodes)"""
        with self._lock:
            self._pending_dimension_docs[dimension] = doc_path

    def flush_dimension_documents(self):
        """Flush accumulated dimension documents to DynamoDB (called after reduction barrier)"""
        with self._lock:
            if not self._pending_dimension_docs:
                return

            self._update_ddb(
                dimension_documents=dict(self._pending_dimension_docs),
                dimension_documents_count=len(self._pending_dimension_docs)
            )

            print(f"📄 Flushed: {len(self._pending_dimension_docs)} dimension documents")

    # ========== Workflow lifecycle methods ==========

    def mark_processing(self):
        """Mark research as processing (called at workflow start)"""
        self.update(
            status='processing',
            created_at=datetime.now(timezone.utc).isoformat()
        )

    def mark_completed(self, **final_data):
        """Mark research as completed (called at workflow end)"""
        with self._lock:
            self._update_ddb(
                status='completed',
                completed_at=datetime.now(timezone.utc).isoformat(),
                **final_data
            )

    def mark_failed(self, error: str):
        """Mark research as failed (called on workflow error)"""
        with self._lock:
            self._update_ddb(
                status='failed',
                error=error,
                failed_at=datetime.now(timezone.utc).isoformat()
            )

    def add_error(self, node_name: str, error_message: str, context: Dict[str, Any] = None):
        """Add an error to the errors list (non-fatal errors during execution)"""
        with self._lock:
            # Get existing errors or initialize
            try:
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                errors = item.get('errors', [])
            except Exception:
                errors = []

            # Append new error
            error_entry = {
                'node': node_name,
                'error': error_message[:500],  # Limit error message length
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            if context:
                error_entry['context'] = context

            errors.append(error_entry)

            # Update DynamoDB
            self._update_ddb(errors=errors)

    def mark_research_failed(self, dimension: str, aspect_name: str, error_message: str):
        """Mark a specific research aspect as failed (for UI display)"""
        with self._lock:
            aspect_key = f"{dimension}::{aspect_name}"

            # Get existing research_by_aspect or initialize
            try:
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                research_by_aspect = dict(item.get('research_by_aspect', {}))
            except Exception:
                research_by_aspect = {}

            # Mark this aspect as failed (metadata only)
            research_by_aspect[aspect_key] = {
                'word_count': 0,
                'sources_count': 0,
                'error': error_message[:200]
            }

            # Update DynamoDB
            self._update_ddb(research_by_aspect=research_by_aspect)
            print(f"❌ Marked research as failed: {aspect_key}")

    def mark_dimension_failed(self, dimension: str, error_message: str):
        """Mark a specific dimension document as failed (for UI display)"""
        with self._lock:
            # Get existing dimension_documents or initialize
            try:
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                dimension_documents = dict(item.get('dimension_documents', {}))
            except Exception:
                dimension_documents = {}

            # Mark this dimension as failed
            dimension_documents[dimension] = {
                'failed': True,
                'error': error_message[:200]
            }

            # Update DynamoDB
            self._update_ddb(dimension_documents=dimension_documents)
            print(f"❌ Marked dimension as failed: {dimension}")

    def update_elapsed_time(self, elapsed_seconds: float):
        """Update elapsed time (can be called periodically)"""
        self.update(elapsed_time=elapsed_seconds)

    # ========== Version and Comment Management ==========

    def create_version(self, version_name: str, markdown_s3_key: str, docx_s3_key: str = None,
                      pdf_s3_key: str = None, created_by: str = 'system',
                      edit_type: str = None, metadata: Dict[str, Any] = None):
        """Create a new version entry in status table

        Args:
            version_name: Version identifier (e.g., 'draft', 'v1', 'v2')
            markdown_s3_key: S3 key for markdown file
            docx_s3_key: S3 key for docx file (optional)
            pdf_s3_key: S3 key for pdf file (optional)
            created_by: User ID or 'system'
            edit_type: Type of edit ('initial', 'smart_edit', 'manual_edit')
            metadata: Additional metadata (comments_count, etc.)
        """
        with self._lock:
            if not self.enabled:
                return

            try:
                # Get existing versions or initialize
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                versions = dict(item.get('versions', {}))

                # Create version entry
                version_entry = {
                    'markdown_s3_key': markdown_s3_key,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'created_by': created_by
                }

                if docx_s3_key:
                    version_entry['docx_s3_key'] = docx_s3_key
                if pdf_s3_key:
                    version_entry['pdf_s3_key'] = pdf_s3_key
                if edit_type:
                    version_entry['edit_type'] = edit_type
                if metadata:
                    version_entry.update(metadata)

                versions[version_name] = version_entry

                # Update DynamoDB
                self._update_ddb(versions=versions)
                print(f"✅ Created version: {version_name}")

            except Exception as e:
                print(f"⚠️  Failed to create version: {e}")

    def set_current_version(self, version: str):
        """Set the current active version

        Args:
            version: Version identifier (e.g., 'draft', 'v1')
        """
        self.update(current_version=version)
        print(f"✅ Set current version to: {version}")

    def add_comment(self, comment_id: str, comment_data: Dict[str, Any]):
        """Add a comment to the status table

        Args:
            comment_id: Unique comment identifier
            comment_data: Comment data including text, selected_text, version, etc.
        """
        with self._lock:
            if not self.enabled:
                return

            try:
                # Get existing comments or initialize
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                comments = list(item.get('comments', []))

                # Add timestamp if not present
                if 'created_at' not in comment_data:
                    comment_data['created_at'] = datetime.now(timezone.utc).isoformat()

                # Add comment
                comment_entry = {
                    'id': comment_id,
                    **comment_data
                }
                comments.append(comment_entry)

                # Update DynamoDB
                self._update_ddb(comments=comments)
                print(f"✅ Added comment: {comment_id}")

            except Exception as e:
                print(f"⚠️  Failed to add comment: {e}")

    def update_comment(self, comment_id: str, updates: Dict[str, Any]):
        """Update an existing comment

        Args:
            comment_id: Comment identifier
            updates: Fields to update
        """
        with self._lock:
            if not self.enabled:
                return

            try:
                # Get existing comments
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                comments = list(item.get('comments', []))

                # Find and update comment
                for comment in comments:
                    if comment.get('id') == comment_id:
                        comment.update(updates)
                        comment['updated_at'] = datetime.now(timezone.utc).isoformat()
                        break

                # Update DynamoDB
                self._update_ddb(comments=comments)
                print(f"✅ Updated comment: {comment_id}")

            except Exception as e:
                print(f"⚠️  Failed to update comment: {e}")

    def delete_comment(self, comment_id: str):
        """Delete a comment

        Args:
            comment_id: Comment identifier
        """
        with self._lock:
            if not self.enabled:
                return

            try:
                # Get existing comments
                response = self.table.get_item(Key={'session_id': self.session_id})
                item = response.get('Item', {})
                comments = list(item.get('comments', []))

                # Filter out the comment
                comments = [c for c in comments if c.get('id') != comment_id]

                # Update DynamoDB
                self._update_ddb(comments=comments)
                print(f"✅ Deleted comment: {comment_id}")

            except Exception as e:
                print(f"⚠️  Failed to delete comment: {e}")

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get current status from DynamoDB (for cancellation checks)"""
        if not self.enabled:
            return None

        try:
            response = self.table.get_item(Key={'session_id': self.session_id})
            return response.get('Item', None)
        except Exception as e:
            print(f"⚠️  Failed to get status from DynamoDB: {e}")
            return None


# ========== Global instance management ==========

_status_updater: Optional[ResearchStatusUpdater] = None
_session_lock = threading.Lock()


def get_status_updater(session_id: str = None) -> Optional[ResearchStatusUpdater]:
    """Get status updater for current session (thread-safe)"""
    global _status_updater

    with _session_lock:
        if _status_updater is None:
            if session_id:
                _status_updater = ResearchStatusUpdater(session_id)
            else:
                print("⚠️  Status updater not initialized")
                return None
        elif session_id and _status_updater.session_id != session_id:
            # New session started, create new updater
            _status_updater = ResearchStatusUpdater(session_id)

    return _status_updater


def set_status_updater(session_id: str) -> ResearchStatusUpdater:
    """Initialize status updater for a new session (thread-safe)"""
    global _status_updater

    with _session_lock:
        _status_updater = ResearchStatusUpdater(session_id)

    return _status_updater


def reset_status_updater():
    """Reset status updater (for testing)"""
    global _status_updater

    with _session_lock:
        _status_updater = None
