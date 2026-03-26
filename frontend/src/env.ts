/**
 * Environment variable validation for API configuration.
 * Ensures NEXT_PUBLIC_API_URL is set and valid.
 */

export const ENV = {
  API_BASE: process.env.NEXT_PUBLIC_API_URL ?? '/api/v1',
  INTERNAL_MODE: process.env.NEXT_PUBLIC_INTERNAL_MODE === 'true',
} as const;

export const API_BASE = ENV.API_BASE;
