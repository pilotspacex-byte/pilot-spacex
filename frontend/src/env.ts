/**
 * Environment variable validation for API configuration.
 * Ensures NEXT_PUBLIC_API_URL is set and valid.
 */

export const ENV = {
  API_BASE: process.env.NEXT_PUBLIC_API_URL,
} as const;

// Validate at build time
if (!ENV.API_BASE) {
  throw new Error(
    'NEXT_PUBLIC_API_URL is not set. Add it to .env.local for development.\n' +
      'Example: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1'
  );
}

if (!ENV.API_BASE.startsWith('http://') && !ENV.API_BASE.startsWith('https://')) {
  throw new Error(`NEXT_PUBLIC_API_URL must start with http:// or https://. Got: ${ENV.API_BASE}`);
}

export const API_BASE = ENV.API_BASE;
