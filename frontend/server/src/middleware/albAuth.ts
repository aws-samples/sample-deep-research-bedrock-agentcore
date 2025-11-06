/**
 * ALB Authentication Middleware
 *
 * Parses user information from ALB authentication headers:
 * - x-amzn-oidc-accesstoken
 * - x-amzn-oidc-identity
 * - x-amzn-oidc-data (JWT with user info)
 *
 * Reference: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html
 */

import { Request, Response, NextFunction } from 'express';

export interface ALBUser {
  sub: string;          // Cognito user ID
  email?: string;
  email_verified?: boolean;
  username?: string;
}

// Extend Express Request type
declare global {
  namespace Express {
    interface Request {
      albUser?: ALBUser;
    }
  }
}

/**
 * Parse ALB OIDC data header
 *
 * The x-amzn-oidc-data header contains a JWT with user claims.
 * Format: header.payload.signature (base64url encoded)
 */
function parseALBOIDCData(oidcData: string): ALBUser | null {
  try {
    // Split JWT into parts
    const parts = oidcData.split('.');
    if (parts.length !== 3) {
      console.error('Invalid JWT format from ALB');
      return null;
    }

    // Decode payload (second part)
    const payload = parts[1];

    // Base64url decode
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = Buffer.from(base64, 'base64').toString('utf-8');
    const claims = JSON.parse(jsonPayload);

    // Extract user information
    const user: ALBUser = {
      sub: claims.sub,
      email: claims.email,
      email_verified: claims.email_verified === 'true' || claims.email_verified === true,
      username: claims['cognito:username'] || claims.username || claims.email
    };

    return user;
  } catch (error) {
    console.error('Error parsing ALB OIDC data:', error);
    return null;
  }
}

/**
 * ALB Authentication Middleware
 *
 * Extracts user information from ALB headers and attaches to req.albUser
 */
export function albAuthMiddleware(req: Request, res: Response, next: NextFunction) {
  // Check for ALB OIDC data header
  const oidcData = req.headers['x-amzn-oidc-data'] as string;

  if (oidcData) {
    const user = parseALBOIDCData(oidcData);
    if (user) {
      req.albUser = user;
      console.log(`✅ ALB Auth: User ${user.email || user.username} (${user.sub})`);
    } else {
      console.warn('⚠️  ALB Auth: Failed to parse OIDC data');
    }
  } else {
    // No ALB auth header - might be local development or health check
    console.log('ℹ️  No ALB auth header found (local development or health check)');
  }

  next();
}

/**
 * Optional: Require authentication
 * Use this middleware on routes that require authentication
 */
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  if (!req.albUser) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Authentication required'
    });
  }
  next();
}
