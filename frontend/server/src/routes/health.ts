import { Router, Request, Response } from 'express';
import { config } from '../config';

const router = Router();

/**
 * GET /api/health
 * Health check endpoint
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'deep-research-bff',
      version: '1.0.0',
      environment: config.server.nodeEnv,
      aws: {
        region: config.aws.region,
      },
      agentcore: {
        configured: !!config.agentcore.runtimeId,
      },
    };

    res.json(health);
  } catch (error: any) {
    console.error('Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      error: error.message,
    });
  }
});

export default router;
