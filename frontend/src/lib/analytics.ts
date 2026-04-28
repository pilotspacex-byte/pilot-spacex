/**
 * Lightweight telemetry shim.
 *
 * Phase 87.1 Plan 04 (CTO-thesis instrumentation): emit named events for
 * AI-generated artifact preview opens so eval dashboards can later answer
 * "did the user actually look at what the agent produced?".
 *
 * Implementation contract:
 *  - In production, route to `window.analytics.track(name, props)` if a
 *    Segment-style global is mounted. We do not depend on any vendor SDK.
 *  - In dev/test, fall back to `console.debug('[analytics]', name, props)`
 *    so events show up in browser/test consoles for verification.
 *  - Server-side rendering: silent no-op.
 *
 * No PII rules apply here; events should already carry only ids + format
 * tokens. Callers are responsible for not passing raw content.
 */

type AnalyticsGlobal = {
  track?: (name: string, props: Record<string, unknown>) => void;
};

export function trackEvent(name: string, props: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as { analytics?: AnalyticsGlobal };
  if (typeof w.analytics?.track === 'function') {
    try {
      w.analytics.track(name, props);
      return;
    } catch (err) {
      // Fall through to console.debug to keep tests non-flaky if a vendor
      // SDK throws.
      console.debug('[analytics] track failed', err);
    }
  }
  if (process.env.NODE_ENV !== 'production') {
    console.debug('[analytics]', name, props);
  }
}
