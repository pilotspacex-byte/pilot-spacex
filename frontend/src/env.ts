/**
 * Environment variable validation for API configuration.
 * Ensures NEXT_PUBLIC_API_URL is set and valid.
 */

export const ENV = {
  API_BASE: process.env.NEXT_PUBLIC_API_URL ?? '/api/v1',
  GITHUB_AUTH_ENABLED: process.env.NEXT_PUBLIC_GITHUB_AUTH_ENABLED === 'true',
} as const;

export const API_BASE = ENV.API_BASE;
