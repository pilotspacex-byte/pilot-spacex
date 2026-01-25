import { NextResponse } from 'next/server';

/**
 * Health check endpoint for Docker/Kubernetes probes
 *
 * Returns:
 * - 200 OK when the application is healthy
 * - Used by Docker HEALTHCHECK and Kubernetes liveness/readiness probes
 */
export async function GET() {
  return NextResponse.json(
    {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'pilot-space-frontend',
    },
    { status: 200 }
  );
}

// Disable caching for health checks
export const dynamic = 'force-dynamic';
