/**
 * Global Application Configuration
 * Single source of truth for all configuration values
 */

export const APP_CONFIG = {
  // API Configuration
  api: {
    baseUrl: process.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 30000, // 30 seconds
  },

  // AWS Configuration
  aws: {
    region: process.env.VITE_AWS_REGION || 'us-west-2',
    agentcore: {
      memoryId: process.env.VITE_AGENTCORE_MEMORY_ID || 'ResearchMemory-2OeNa02agH',
    },
    cognito: {
      userPoolId: process.env.VITE_USER_POOL_ID || '',
      clientId: process.env.VITE_USER_POOL_CLIENT_ID || '',
      region: process.env.VITE_AWS_REGION || 'us-west-2',
    },
  },

  // Polling Configuration
  polling: {
    interval: parseInt(process.env.VITE_POLLING_INTERVAL) || 5000, // 5 seconds
    maxRetries: 3,
  },

  // Research Configuration
  research: {
    defaultType: 'basic_web',
    defaultDepth: 'balanced',
    maxConcurrent: 3,
  },

  // UI Configuration
  ui: {
    pageSize: 20,
    notificationDuration: 5000, // 5 seconds
  },

  // Feature Flags
  features: {
    authentication: process.env.VITE_ENABLE_AUTH === 'true',
    downloads: true,
    advancedSettings: true,
  },

  // Environment
  env: import.meta.env.MODE || 'development',
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

// Validate required configuration
export function validateConfig() {
  const errors = [];

  if (!APP_CONFIG.api.baseUrl) {
    errors.push('API base URL is not configured');
  }

  if (APP_CONFIG.features.authentication) {
    if (!APP_CONFIG.aws.cognito.userPoolId) {
      errors.push('Cognito User Pool ID is required when authentication is enabled');
    }
    if (!APP_CONFIG.aws.cognito.clientId) {
      errors.push('Cognito Client ID is required when authentication is enabled');
    }
  }

  if (errors.length > 0) {
    console.error('Configuration validation errors:', errors);
    return false;
  }

  return true;
}

// Helper function to get AWS region
export function getAwsRegion() {
  return APP_CONFIG.aws.region;
}

// Helper function to get API base URL
export function getApiBaseUrl() {
  return APP_CONFIG.api.baseUrl;
}

// Helper function to get polling interval
export function getPollingInterval() {
  return APP_CONFIG.polling.interval;
}

export default APP_CONFIG;
