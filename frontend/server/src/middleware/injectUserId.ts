/**
 * User ID Injection Middleware
 *
 * Injects verified user ID from ALB authentication into request headers.
 * This prevents clients from spoofing user IDs by overriding the x-user-id header
 * with the authenticated user ID from ALB OIDC.
 *
 * Security: Always uses req.albUser.sub from ALB authentication, ignoring client-provided headers.
 */

import { Request, Response, NextFunction } from 'express';
import { config } from '../config';

/**
 * Inject verified user ID from authentication
 *
 * This middleware must be placed AFTER albAuthMiddleware or validateCognitoToken
 *
 * SECURITY: Only uses verified user IDs from authentication middleware.
 * NEVER trusts client-provided x-user-id headers.
 */
export function injectVerifiedUserId(req: Request, res: Response, next: NextFunction) {
  // ALWAYS delete any client-provided x-user-id header to prevent spoofing
  const clientProvidedId = req.headers['x-user-id'];
  if (clientProvidedId) {
    console.warn(`⚠️  Client attempted to provide x-user-id: ${String(clientProvidedId).substring(0, 8)}... (IGNORED)`);
    delete req.headers['x-user-id'];
  }

  // Use verified user ID from authentication middleware (ALB or JWT)
  if (req.albUser?.sub) {
    // Override with verified user ID from authentication
    req.headers['x-user-id'] = req.albUser.sub;
    console.log(`✅ Injected verified user ID: ${req.albUser.sub.substring(0, 8)}...`);
  } else if (config.auth.enabled) {
    // Authentication is enabled but no verified user: reject
    console.error('❌ No verified user ID available - authentication required');
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Authentication required'
    });
  } else {
    // Authentication is disabled: allow anonymous access for development/testing
    req.headers['x-user-id'] = 'anonymous';
    console.warn('⚠️  Authentication disabled - using anonymous user ID (DEVELOPMENT ONLY)');
  }

  next();
}
