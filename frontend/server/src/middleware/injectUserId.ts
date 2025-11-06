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

/**
 * Inject verified user ID from ALB authentication
 *
 * This middleware must be placed AFTER albAuthMiddleware
 */
export function injectVerifiedUserId(req: Request, res: Response, next: NextFunction) {
  // Use verified user ID from ALB authentication
  if (req.albUser?.sub) {
    // Override any client-provided x-user-id with verified ALB user ID
    req.headers['x-user-id'] = req.albUser.sub;
    console.log(`✅ Injected verified user ID from ALB: ${req.albUser.sub.substring(0, 8)}...`);
  } else if (req.headers['x-user-id']) {
    // Client provided user ID (from React Amplify Cognito)
    // Keep the client-provided user ID
    console.log(`ℹ️  Using client-provided user ID: ${String(req.headers['x-user-id']).substring(0, 8)}...`);
  } else {
    // No authentication: use anonymous
    req.headers['x-user-id'] = 'anonymous';
    console.log('ℹ️  No authentication: using anonymous user ID');
  }

  next();
}
