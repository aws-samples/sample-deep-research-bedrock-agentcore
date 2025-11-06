/**
 * Authentication routes
 * Provides user information from ALB authentication
 */

import express, { Request, Response } from 'express';

const router = express.Router();

/**
 * GET /api/auth/user
 * Returns current user information from ALB headers
 */
router.get('/user', (req: Request, res: Response) => {
  if (req.albUser) {
    return res.json({
      authenticated: true,
      user: {
        id: req.albUser.sub,
        email: req.albUser.email,
        username: req.albUser.username,
        emailVerified: req.albUser.email_verified
      }
    });
  }

  // No ALB auth (local development)
  return res.json({
    authenticated: false,
    user: {
      id: 'local-dev',
      email: 'dev@localhost',
      username: 'Local Developer',
      emailVerified: true
    }
  });
});

/**
 * POST /api/auth/logout
 * Redirect to ALB logout (clears session cookie)
 */
router.post('/logout', (req: Request, res: Response) => {
  // ALB logout is handled by ALB itself
  // Frontend should redirect to CloudFront URL to trigger re-authentication
  res.json({
    success: true,
    message: 'Logged out. Please refresh the page.'
  });
});

export default router;
