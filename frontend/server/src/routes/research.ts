import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import {
  createOrUpdateStatus,
  getStatus,
  getStatusForUser,
  updateStatus,
  listStatus,
  deleteStatus,
  getComments,
  addComment,
  updateComment,
  deleteComment,
  addCommentReply,
  getVersions,
  getCurrentVersion,
} from '../services/dynamodb';
import { invokeResearchWorkflow, queryAgentCoreMemory, getEventDetails } from '../services/agentcore';
import { generateDownloadLinks } from '../services/s3';
import { CreateResearchRequest, ResearchStatus } from '../types';

const router = Router();

// Configure multer for PDF file uploads (in-memory storage)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 4.5 * 1024 * 1024, // 4.5MB limit
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'));
    }
  },
});

/**
 * POST /api/research
 * Create a new research session and start workflow
 * Supports multipart/form-data for PDF uploads
 */
router.post('/', upload.any(), async (req: Request, res: Response) => {
  try {
    // Get user ID from header (set by Cognito authentication)
    const userId = req.headers['x-user-id'] as string;

    // Validate user ID is present
    if (!userId) {
      return res.status(401).json({
        error: 'Missing required header: x-user-id (authentication required)',
      });
    }

    // Parse JSON fields from form data
    const { topic, research_type, research_depth, llm_model, research_context, reference_materials_json } = req.body;

    // Validate request
    if (!topic || !research_type || !research_depth) {
      return res.status(400).json({
        error: 'Missing required fields: topic, research_type, research_depth',
      });
    }

    // Process reference materials with PDF bytes
    let referenceMaterials: any[] = [];
    if (reference_materials_json) {
      try {
        referenceMaterials = JSON.parse(reference_materials_json);

        // Attach PDF bytes to reference materials
        const files = (req.files as Express.Multer.File[]) || [];
        referenceMaterials.forEach((ref, index) => {
          if (ref.type === 'pdf') {
            const file = files.find((f) => f.fieldname === `pdf_${index}`);
            if (file) {
              // Convert buffer to base64 string for JSON transport to AgentCore
              ref.pdf_bytes_base64 = file.buffer.toString('base64');
              ref.filename = file.originalname;
              ref.title = ref.title || file.originalname;
              console.log(`✅ Attached PDF: ${file.originalname} (${file.size} bytes, base64: ${ref.pdf_bytes_base64.length} chars)`);
            }
          }
        });
      } catch (error: any) {
        console.error('Failed to parse reference_materials_json:', error);
        return res.status(400).json({
          error: 'Invalid reference_materials_json format',
        });
      }
    }

    // Create session with user ID prefix
    const sessionId = `${userId}-${Date.now()}`;
    const now = new Date().toISOString();

    // Create initial status (single source of truth)
    const status: ResearchStatus = {
      session_id: sessionId,
      user_id: userId,
      status: 'pending',
      topic,
      research_type,
      research_depth,
      research_context,
      created_at: now,
      updated_at: now,
    };

    await createOrUpdateStatus(status);

    // Invoke AgentCore Runtime workflow (async)
    invokeResearchWorkflow(sessionId, {
      topic,
      researchConfig: {
        research_type,
        research_depth,
        llm_model: llm_model || 'nova_pro',
        research_context,
        reference_materials: referenceMaterials.length > 0 ? referenceMaterials : undefined,
      },
      userId: userId,
    })
      .then(async () => {
        // Update status to processing
        await updateStatus(sessionId, { status: 'processing' });
      })
      .catch(async (error) => {
        console.error(`Failed to start workflow for ${sessionId}:`, error);
        await updateStatus(sessionId, {
          status: 'failed',
          error: error.message,
        });
      });

    res.status(201).json({
      session_id: sessionId,
      status: 'pending',
      message: 'Research session created successfully',
    });
  } catch (error: any) {
    console.error('Failed to create research session:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/history
 * Get research history
 * IMPORTANT: Must come before /:sessionId route to avoid matching "history" as sessionId
 */
router.get('/history', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;

    if (!userId) {
      return res.status(401).json({
        error: 'Missing required header: x-user-id (authentication required)',
      });
    }

    const limit = parseInt(req.query.limit as string) || 50;

    const sessions = await listStatus(userId, limit);

    res.json({ sessions, count: sessions.length });
  } catch (error: any) {
    console.error('Failed to get research history:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/reviews
 * Get all research reviews for the current user
 * IMPORTANT: Must come before /:sessionId route to avoid matching "reviews" as sessionId
 */
router.get('/reviews', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;

    if (!userId) {
      return res.status(401).json({
        error: 'Missing required header: x-user-id (authentication required)',
      });
    }

    const limit = parseInt(req.query.limit as string) || 50;

    // Get all completed research sessions for the user
    const sessions = await listStatus(userId, limit);

    // Filter for completed research and map to review format
    const reviews = sessions
      .filter(session => session.status === 'completed')
      .map(session => {
        const comments = session.comments || [];
        const pendingCount = comments.filter((c: any) => c.status === 'pending').length;
        const resolvedCount = comments.filter((c: any) => c.status === 'resolved').length;

        return {
          session_id: session.session_id,
          topic: session.topic,
          research_type: session.research_type,
          status: session.status,
          review_status: session.review_status || 'not_started',
          review_version: session.review_version || session.current_version || 'draft',
          review_base_version: session.review_base_version,
          review_started_at: session.review_started_at,
          review_completed_at: session.review_completed_at,
          pending_comments_count: session.pending_comments_count || pendingCount,
          resolved_comments_count: session.resolved_comments_count || resolvedCount,
          created_at: session.created_at,
          updated_at: session.updated_at,
        };
      });

    res.json({ reviews, count: reviews.length });
  } catch (error: any) {
    console.error('Failed to get research reviews:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId
 * Get research session status
 */
router.get('/:sessionId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    res.json(status);
  } catch (error: any) {
    console.error('Failed to get research status:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/results
 * Get research results
 */
router.get('/:sessionId/results', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (status.status !== 'completed') {
      return res.status(400).json({
        error: 'Research not completed yet',
        status: status.status,
      });
    }

    // TODO: Fetch detailed workflow state from AgentCore checkpointer
    // For now, return metadata from DynamoDB
    res.json({
      session_id: sessionId,
      topic: status.topic,
      status: status.status,
      research_type: status.research_type,
      research_depth: status.research_depth,
      report_file: status.report_file,
      dimension_documents: status.dimension_documents,
      created_at: status.created_at,
      completed_at: status.completed_at || status.updated_at,
    });
  } catch (error: any) {
    console.error('Failed to get research results:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/download
 * Generate presigned download links for research outputs
 */
router.get('/:sessionId/download', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const version = (req.query.version as string) || 'draft';

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (status.status !== 'completed') {
      return res.status(400).json({
        error: 'Research not completed yet',
        status: status.status,
      });
    }

    // Generate presigned URLs (expires in 1 hour)
    const links = await generateDownloadLinks(sessionId, 3600, version);

    res.json({
      session_id: sessionId,
      version,
      downloads: links,
    });
  } catch (error: any) {
    console.error('Failed to generate download links:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PATCH /api/research/:sessionId/cancel
 * Cancel ongoing research session
 */
router.patch('/:sessionId/cancel', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Only allow cancellation of processing research
    if (status.status !== 'processing') {
      return res.status(400).json({
        error: `Cannot cancel research with status: ${status.status}`,
        current_status: status.status,
      });
    }

    // Update status to cancelling (workflow will set to cancelled when stopped)
    await updateStatus(sessionId, {
      status: 'cancelling',
    });

    console.log(`🛑 Research cancellation requested: ${sessionId}`);

    res.json({
      message: 'Research cancellation requested',
      session_id: sessionId,
      status: 'cancelling',
    });
  } catch (error: any) {
    console.error('Failed to cancel research session:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/research/:sessionId
 * Delete research session
 */
router.delete('/:sessionId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Delete from DynamoDB (status table)
    await deleteStatus(sessionId);

    res.json({
      message: 'Research session deleted successfully',
      session_id: sessionId,
    });
  } catch (error: any) {
    console.error('Failed to delete research session:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/memory/events
 * Get AgentCore Memory events for a research session
 */
router.get('/:sessionId/memory/events', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const maxResults = parseInt(req.query.max_results as string) || 100;

    // Get user ID from session
    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Use actual user_id from status (matches how events are created in workflow)
    const actorId = status.user_id;

    if (!actorId) {
      console.error(`⚠️  user_id not found for session ${sessionId} - cannot query events`);
      return res.status(400).json({
        error: 'user_id not found for this session - event tracking may not be configured properly'
      });
    }

    // Query AgentCore Memory
    const events = await queryAgentCoreMemory(sessionId, actorId, maxResults);

    res.json({
      session_id: sessionId,
      actor_id: actorId,
      events,
      count: events.length,
    });
  } catch (error: any) {
    console.error('Failed to get memory events:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/memory/events/:eventId
 * Get detailed event information from AgentCore Memory
 */
router.get('/:sessionId/memory/events/:eventId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId, eventId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Get actor ID from status
    const actorId = status.user_id;

    if (!actorId) {
      return res.status(400).json({
        error: 'user_id not found for this session - event tracking not configured properly'
      });
    }

    // Get event details
    const event = await getEventDetails(eventId, sessionId, actorId);

    res.json({
      session_id: sessionId,
      event,
    });
  } catch (error: any) {
    console.error('Failed to get event details:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/markdown
 * Get markdown content for review
 */
router.get('/:sessionId/markdown', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const version = (req.query.version as string) || 'draft';

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Get markdown content from AgentCore Memory or S3
    const { getMarkdownContent } = await import('../services/markdown');
    const markdown = await getMarkdownContent(sessionId, version);

    res.json({
      session_id: sessionId,
      version,
      content: markdown,
    });
  } catch (error: any) {
    console.error('Failed to get markdown content:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/comments
 * Get all comments for a research session
 */
router.get('/:sessionId/comments', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Get comments from Status table
    const comments = await getComments(sessionId);

    res.json({
      session_id: sessionId,
      comments,
      count: comments.length,
    });
  } catch (error: any) {
    console.error('Failed to get comments:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/research/:sessionId/comments
 * Add a comment to a research session
 */
router.post('/:sessionId/comments', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const comment = req.body;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Save comment to Status table
    await addComment(sessionId, comment);

    res.status(201).json({
      message: 'Comment added successfully',
      comment,
    });
  } catch (error: any) {
    console.error('Failed to add comment:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PUT /api/research/:sessionId/comments/:commentId
 * Update a comment
 */
router.put('/:sessionId/comments/:commentId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId, commentId } = req.params;
    const updates = req.body;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Update comment in Status table
    await updateComment(sessionId, commentId, updates);

    res.json({
      message: 'Comment updated successfully',
      comment_id: commentId,
    });
  } catch (error: any) {
    console.error('Failed to update comment:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/research/:sessionId/comments/:commentId
 * Delete a comment
 */
router.delete('/:sessionId/comments/:commentId', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId, commentId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Delete comment from Status table
    await deleteComment(sessionId, commentId);

    res.json({
      message: 'Comment deleted successfully',
      comment_id: commentId,
    });
  } catch (error: any) {
    console.error('Failed to delete comment:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/research/:sessionId/comments/:commentId/replies
 * Add a reply to a comment
 */
router.post('/:sessionId/comments/:commentId/replies', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId, commentId } = req.params;
    const reply = req.body;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Add reply to comment in Status table
    await addCommentReply(sessionId, commentId, reply);

    res.status(201).json({
      message: 'Reply added successfully',
      comment_id: commentId,
    });
  } catch (error: any) {
    console.error('Failed to add reply:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/research/:sessionId/charts/:filename
 * Get presigned URL for chart image
 */
router.get('/:sessionId/charts/:filename', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId, filename } = req.params;

    // Verify user ownership
    const status = await getStatusForUser(sessionId, userId);
    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Generate presigned URL for the chart image
    const { generateChartImageUrl } = await import('../services/s3');
    const imageUrl = await generateChartImageUrl(sessionId, filename, 3600);

    // Return the presigned URL as JSON
    res.json({ url: imageUrl });
  } catch (error: any) {
    console.error('Failed to get chart image URL:', error);
    res.status(404).json({ error: 'Image not found' });
  }
});

/**
 * GET /api/research/:sessionId/versions
 * Get all versions for a research session
 */
router.get('/:sessionId/versions', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Get versions from Status table
    const versions = await getVersions(sessionId);
    const currentVersion = await getCurrentVersion(sessionId);

    res.json({
      session_id: sessionId,
      current_version: currentVersion,
      versions,
    });
  } catch (error: any) {
    console.error('Failed to get versions:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/research/:sessionId/review
 * Start a review for a research session
 */
router.post('/:sessionId/review', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const { version, base_version } = req.body;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    if (status.status !== 'completed') {
      return res.status(400).json({
        error: 'Can only review completed research',
        status: status.status,
      });
    }

    // Update review metadata
    const reviewVersion = version || status.current_version || 'draft';
    await updateStatus(sessionId, {
      review_status: 'draft',
      review_version: reviewVersion,
      review_base_version: base_version,
      review_started_at: new Date().toISOString(),
    });

    res.json({
      message: 'Review started successfully',
      session_id: sessionId,
      review_version: reviewVersion,
      review_status: 'draft',
    });
  } catch (error: any) {
    console.error('Failed to start review:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PATCH /api/research/:sessionId/review
 * Update review status
 */
router.patch('/:sessionId/review', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string;
    const { sessionId } = req.params;
    const { review_status, pending_comments_count, resolved_comments_count } = req.body;

    const status = await getStatusForUser(sessionId, userId);

    if (!status) {
      return res.status(404).json({ error: 'Session not found' });
    }

    const updates: any = {};

    if (review_status) {
      updates.review_status = review_status;

      // If approved, set completed timestamp
      if (review_status === 'approved') {
        updates.review_completed_at = new Date().toISOString();
      }
    }

    if (typeof pending_comments_count === 'number') {
      updates.pending_comments_count = pending_comments_count;
    }

    if (typeof resolved_comments_count === 'number') {
      updates.resolved_comments_count = resolved_comments_count;
    }

    await updateStatus(sessionId, updates);

    res.json({
      message: 'Review status updated successfully',
      session_id: sessionId,
      updates,
    });
  } catch (error: any) {
    console.error('Failed to update review status:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
