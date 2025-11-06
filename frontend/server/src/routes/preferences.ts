import { Router, Request, Response } from 'express';
import { getUserPreferences, saveUserPreferences } from '../services/dynamodb';
import { UserPreferences } from '../types';

const router = Router();

/**
 * GET /api/preferences
 * Get user preferences
 * Auto-creates default preferences for new users
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';

    let preferences = await getUserPreferences(userId);

    // Create default preferences for new users
    if (!preferences) {
      console.log(`📝 Creating default preferences for new user: ${userId}`);

      const now = new Date().toISOString();
      const defaultPreferences: UserPreferences = {
        user_id: userId,
        default_chat_model: 'claude_haiku45',
        default_research_model: 'claude_haiku45',
        default_research_type: 'web',
        default_research_depth: 'quick',
        created_at: now,
        updated_at: now,
      };

      await saveUserPreferences(defaultPreferences);

      console.log(`✅ Default preferences created for user: ${userId}`);
      preferences = defaultPreferences;
    }

    res.json(preferences);
  } catch (error: any) {
    console.error('Failed to get user preferences:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PUT /api/preferences
 * Update user preferences
 */
router.put('/', async (req: Request, res: Response) => {
  try {
    const userId = req.headers['x-user-id'] as string || 'anonymous';
    const { default_chat_model, default_research_model, default_research_type, default_research_depth } = req.body;

    // Validate required fields
    if (!default_chat_model || !default_research_model || !default_research_type || !default_research_depth) {
      return res.status(400).json({
        error: 'Missing required fields: default_chat_model, default_research_model, default_research_type, default_research_depth',
      });
    }

    const preferences: UserPreferences = {
      user_id: userId,
      default_chat_model,
      default_research_model,
      default_research_type,
      default_research_depth,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    await saveUserPreferences(preferences);

    res.json({
      message: 'Preferences saved successfully',
      preferences,
    });
  } catch (error: any) {
    console.error('Failed to save user preferences:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
