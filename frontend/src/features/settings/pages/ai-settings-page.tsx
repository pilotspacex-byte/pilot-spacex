/**
 * AISettingsPage - Workspace AI configuration.
 *
 * Unified provider list with expandable rows.
 * All 6 providers (Anthropic, OpenAI, Google Gemini, Kimi, GLM, AI Agent)
 * appear in a single list. Each row is expandable with provider-specific fields.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { ProviderRow } from '../components/provider-row';
import { AIFeatureToggles } from '../components/ai-feature-toggles';
import { useStore } from '@/stores';

const ALL_PROVIDERS = ['anthropic', 'openai', 'google', 'kimi', 'glm', 'ai_agent'] as const;

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-[300px] w-full" />
      <Skeleton className="h-[400px] w-full" />
    </div>
  );
}

export const AISettingsPage = observer(function AISettingsPage() {
  const { ai, workspaceStore } = useStore();
  const { settings } = ai;
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  React.useEffect(() => {
    if (workspaceId) {
      settings.loadSettings(workspaceId);
    }
  }, [workspaceId, settings]);

  const handleProviderSaved = () => {
    settings.loadSettings(workspaceId);
    settings.loadModels(workspaceId);
  };

  if (settings.isLoading) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (settings.error && !settings.settings) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load settings</AlertTitle>
          <AlertDescription>{settings.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">AI Providers</h1>
          <p className="text-sm text-muted-foreground">
            Configure AI provider API keys and manage AI-powered features for your workspace.
          </p>
        </div>

        {/* Unified Provider List */}
        <div className="space-y-2">
          {ALL_PROVIDERS.map((provider) => (
            <ProviderRow
              key={provider}
              provider={provider}
              status={settings.getProviderStatus(provider)}
              onSaved={handleProviderSaved}
            />
          ))}
        </div>

        <Separator />

        {/* Feature Toggles */}
        <AIFeatureToggles />

        {/* Info Alert */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Security & Privacy</AlertTitle>
          <AlertDescription>
            API keys are encrypted using Supabase Vault before storage. Keys are never logged or
            exposed in responses. Each AI request is tracked for cost monitoring and audit purposes.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
});
