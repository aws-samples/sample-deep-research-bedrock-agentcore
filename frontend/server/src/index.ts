import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import path from 'path';
import fs from 'fs';
import { config, loadConfigFromSSM, validateConfig } from './config';
import { logger } from './middleware/logger';
import { errorHandler } from './middleware/errorHandler';
import { albAuthMiddleware } from './middleware/albAuth';
import { validateCognitoToken } from './middleware/cognitoAuth';
import { injectVerifiedUserId } from './middleware/injectUserId';
import researchRoutes from './routes/research';
import healthRoutes from './routes/health';
import authRoutes from './routes/auth';
import preferencesRoutes from './routes/preferences';
import chatRoutes from './routes/chat';

// Async initialization
async function initialize() {
  try {
    // Load configuration from SSM Parameter Store
    await loadConfigFromSSM();

    // Validate configuration
    validateConfig();
  } catch (error: any) {
    console.error('❌ Initialization failed:', error.message);
    process.exit(1);
  }
}

const app = express();

// Trust proxy for rate limiting (ALB/ELB sends X-Forwarded-For header)
app.set('trust proxy', true);

// Middleware
const awsRegion = config.aws.region;
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: [
        "'self'",
        `https://cognito-idp.${awsRegion}.amazonaws.com`,
        `https://cognito-identity.${awsRegion}.amazonaws.com`,
        `https://*.auth.${awsRegion}.amazoncognito.com`
      ],
      fontSrc: ["'self'", "data:"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
}));
app.use(cors({
  origin: config.cors.origin,
  credentials: true,
}));
app.use(express.json());
app.use(logger);

// Health check endpoint (no auth required for ALB health checks)
app.use('/api/health', healthRoutes);

/**
 * Rate Limiting for API endpoints
 * Protects against brute force attacks and DoS attempts
 * Settings are generous to not affect normal users
 */
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 150, // Limit each IP to 150 requests per windowMs (very generous)
  standardHeaders: true, // Return rate limit info in `RateLimit-*` headers
  legacyHeaders: false, // Disable `X-RateLimit-*` headers
  message: {
    error: 'Too many requests from this IP, please try again later.',
    retryAfter: 'Check the Retry-After header for wait time.'
  },
  // Skip rate limiting for health checks
  skip: (req) => req.path === '/api/health'
});

// Apply rate limiter to all API routes
app.use('/api', apiLimiter);

/**
 * Hybrid Authentication Strategy
 *
 * 1. ALB Authentication (Production):
 *    - ALB injects x-amzn-oidc-data header with verified JWT
 *    - albAuthMiddleware parses it and populates req.albUser
 *
 * 2. Direct JWT Authentication (Local Development):
 *    - Client sends Authorization: Bearer <jwt> header
 *    - validateCognitoToken verifies JWT and populates req.albUser
 *
 * 3. User ID Injection:
 *    - injectVerifiedUserId takes req.albUser.sub and injects as x-user-id
 *    - NEVER trusts client-provided x-user-id headers
 */
app.use('/api', (req, res, next) => {
  // Try ALB authentication first (production)
  albAuthMiddleware(req, res, (err) => {
    if (err) {
      return next(err);
    }

    // If ALB auth succeeded, continue to user ID injection
    if (req.albUser) {
      return next();
    }

    // ALB auth not available, try direct JWT authentication (local dev)
    validateCognitoToken(req, res, next);
  });
});

// Inject verified user ID (after authentication)
app.use('/api', injectVerifiedUserId);

// Protected API routes
app.use('/api/auth', authRoutes);
app.use('/api/research', researchRoutes);
app.use('/api/preferences', preferencesRoutes);
app.use('/api/chat', chatRoutes);

// Serve React static files
// Path differs between local and Docker:
// Local:  frontend/server/dist/../../build = frontend/build
// Docker: /app/server/dist/../../frontend/build = /app/frontend/build
//
// Try multiple possible paths and use the first one that exists
const possiblePaths = [
  path.join(__dirname, '../../frontend/build'),  // Docker
  path.join(__dirname, '../../build'),            // Local compiled
  path.join(__dirname, '../../../build')          // Local dev mode
];

let frontendBuildPath: string | undefined;
for (const testPath of possiblePaths) {
  try {
    if (fs.existsSync(path.join(testPath, 'index.html'))) {
      frontendBuildPath = testPath;
      console.log('✅ Found frontend build at:', frontendBuildPath);
      break;
    } else {
      console.log('❌ No index.html at:', testPath);
    }
  } catch (e) {
    console.log('❌ Cannot access:', testPath);
  }
}

if (!frontendBuildPath) {
  console.error('❌ CRITICAL: Could not find frontend build directory!');
  console.error('Tried paths:', possiblePaths);
  console.error('Current __dirname:', __dirname);
  process.exit(1);
}

console.log('📦 Serving static files from:', frontendBuildPath);
app.use(express.static(frontendBuildPath));

// Catch-all route to serve React app (for client-side routing)
app.get('*', (req, res) => {
  res.sendFile(path.join(frontendBuildPath!, 'index.html'));
});

// Error handler (must be last)
app.use(errorHandler);

// Start server after initialization
async function startServer() {
  await initialize();

  const server = app.listen(config.server.port, () => {
    console.log('\n' + '='.repeat(80));
    console.log('🚀 Deep Research Agent BFF Server');
    console.log('='.repeat(80));
    console.log(`📡 Server running on port ${config.server.port}`);
    console.log(`🌍 Environment: ${config.server.nodeEnv}`);
    console.log(`🌐 CORS Origin: ${config.cors.origin}`);
    console.log('='.repeat(80));
    console.log('\n📋 Available endpoints:');
    console.log('  GET  /api/health');
    console.log('  GET  /api/auth/user');
    console.log('  POST /api/auth/logout');
    console.log('  POST /api/research');
    console.log('  GET  /api/research/:sessionId');
    console.log('  GET  /api/research/:sessionId/results');
    console.log('  GET  /api/research/history');
    console.log('  DELETE /api/research/:sessionId');
    console.log('  GET  /api/research/:sessionId/download');
    console.log('='.repeat(80) + '\n');
  });

  // Set generous timeouts for long-running research operations
  server.timeout = 3600000; // 1 hour (in milliseconds)
  server.keepAliveTimeout = 3600000; // 1 hour
  server.headersTimeout = 3610000; // Slightly more than keepAliveTimeout
}

startServer().catch(error => {
  console.error('Failed to start server:', error);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\nSIGINT received, shutting down gracefully...');
  process.exit(0);
});
