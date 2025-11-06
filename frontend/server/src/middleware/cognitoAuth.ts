/**
 * Cognito JWT Authentication Middleware
 *
 * Validates Cognito JWT tokens for direct client authentication.
 * This is used as a fallback when ALB authentication is not available (e.g., local development).
 *
 * Security: Uses JWKS to verify token signature against Cognito's public keys.
 */

import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';
import { Request, Response, NextFunction } from 'express';
import { config } from '../config';

// JWKS client for fetching Cognito public keys
const client = jwksClient({
  jwksUri: `https://cognito-idp.${config.aws.region}.amazonaws.com/${config.auth.cognitoUserPoolId}/.well-known/jwks.json`,
  cache: true,
  cacheMaxAge: 600000, // 10 minutes
  rateLimit: true,
  jwksRequestsPerMinute: 10
});

// Get signing key from JWKS
function getKey(header: any, callback: any) {
  client.getSigningKey(header.kid, (err, key) => {
    if (err) {
      return callback(err);
    }
    const signingKey = key?.getPublicKey();
    callback(null, signingKey);
  });
}

/**
 * Validate Cognito JWT token
 *
 * Verifies:
 * 1. Token signature using JWKS
 * 2. Token issuer matches Cognito User Pool
 * 3. Token is not expired
 * 4. Token audience (client ID) matches
 */
export function validateCognitoToken(req: Request, res: Response, next: NextFunction) {
  // Skip if authentication is disabled
  if (!config.auth.enabled) {
    console.log('ℹ️  Authentication disabled, skipping JWT validation');
    return next();
  }

  // Extract token from Authorization header
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'No authorization header provided'
    });
  }

  const token = authHeader.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Invalid authorization header format'
    });
  }

  // Verify token
  jwt.verify(token, getKey, {
    issuer: `https://cognito-idp.${config.aws.region}.amazonaws.com/${config.auth.cognitoUserPoolId}`,
    audience: config.auth.cognitoClientId,
    algorithms: ['RS256']
  }, (err, decoded: any) => {
    if (err) {
      console.error('❌ JWT verification failed:', err.message);
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      });
    }

    // Attach verified user info to request
    req.albUser = {
      sub: decoded.sub,
      email: decoded.email,
      email_verified: decoded.email_verified === 'true' || decoded.email_verified === true,
      username: decoded['cognito:username'] || decoded.username || decoded.email
    };

    console.log(`✅ JWT Auth: User ${req.albUser.email || req.albUser.username} (${req.albUser.sub.substring(0, 8)}...)`);
    next();
  });
}
