'use client';

/**
 * AiNotConfiguredBanner - Workspace-level banner shown to Owners when no BYOK API key
 * is configured (AIGOV-05).
 *
 * - Visible to Owner only (isOwner=false returns null immediately)
 * - Queries ai-status endpoint lazily — only fetches when isOwner=true
 * - Dismissable per browser session (sessionStorage key; resets on next browser session)
 * - Links to Settings > AI Providers
 * - Non-Owner members: no banner; AI controls simply disabled without explanation
 */

import { useState } from 'react';
import { X } from 'lucide-react';
import Link from 'next/link';
import { useAIStatus } from '@/hooks/use-ai-status';

const DISMISS_KEY = 'ai_banner_dismissed';

interface AiNotConfiguredBannerProps {
  workspaceSlug: string;
  isOwner: boolean;
}

export function AiNotConfiguredBanner({ workspaceSlug, isOwner }: AiNotConfiguredBannerProps) {
  const [dismissed, setDismissed] = useState(
    () => typeof window !== 'undefined' && sessionStorage.getItem(DISMISS_KEY) === 'true'
  );

  // Only fetch AI status for owners — non-owners never see this banner
  const { data } = useAIStatus(isOwner ? workspaceSlug : '');

  // Guard: non-owner, already dismissed, or AI is configured
  if (!isOwner || dismissed || data?.byok_configured !== false) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between text-sm"
    >
      <span className="text-amber-800">
        AI features are disabled — no API key configured.{' '}
        <Link
          href={`/${workspaceSlug}/settings/ai-providers`}
          className="underline font-medium hover:text-amber-900"
        >
          Configure a key in Settings
        </Link>
      </span>
      <button
        type="button"
        onClick={() => {
          sessionStorage.setItem(DISMISS_KEY, 'true');
          setDismissed(true);
        }}
        className="ml-4 text-amber-600 hover:text-amber-800 shrink-0"
        aria-label="Dismiss AI configuration notice"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
