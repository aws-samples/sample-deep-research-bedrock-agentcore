/**
 * AWS Amplify Configuration for Cognito Authentication
 */

import { APP_CONFIG } from './config/app.config';

export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: APP_CONFIG.aws.cognito.userPoolId,
      userPoolClientId: APP_CONFIG.aws.cognito.clientId,
      region: APP_CONFIG.aws.cognito.region,
      loginWith: {
        email: true,
      },
      signUpVerificationMethod: 'code',
      userAttributes: {
        email: {
          required: true,
        },
      },
      allowGuestAccess: false,
      passwordFormat: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireNumbers: true,
        requireSpecialCharacters: true,
      },
    },
  },
};
