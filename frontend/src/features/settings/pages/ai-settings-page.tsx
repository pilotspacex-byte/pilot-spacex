/**
 * AISettingsPage - Workspace AI configuration.
 *
 * T178: Main settings page with API keys, feature toggles, provider status.
 * 13-03: Expanded to show all 5 built-in providers + custom provider registration.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { APIKeyForm } from '../components/api-key-form';
import { AIFeatureToggles } from '../components/ai-feature-toggles';
import { ProviderStatusCard } from '../components/provider-status-card';
import { CustomProviderForm } from '../components/custom-provider-form';
import { useStore } from '@/stores';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';

const BUILT_IN_PROVIDERS = ['anthropic', 'openai', 'kimi', 'glm', 'google'] as const;

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

  const getProviderStatus = (provider: string): WorkspaceAISettingsProvider | undefined =>
    settings.settings?.providers?.find((p) => p.provider === provider);

  const customProviders =
    settings.settings?.providers?.filter((p) => p.provider === 'custom') ?? [];

  const handleCustomProviderSuccess = () => {
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

        {/* Provider Status Cards — all 5 built-in providers */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Provider Status</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {BUILT_IN_PROVIDERS.map((provider) => {
              const providerData = getProviderStatus(provider);
              return (
                <ProviderStatusCard
                  key={provider}
                  provider={provider}
                  isKeySet={providerData?.isConfigured ?? false}
                  lastValidated={providerData?.lastValidatedAt}
                  status={providerData?.isValid ? 'connected' : 'unknown'}
                />
              );
            })}
          </div>
        </div>

        <Separator />

        {/* API Key Configuration */}
        <APIKeyForm />

        <Separator />

        {/* Feature Toggles */}
        <AIFeatureToggles />

        <Separator />

        {/* Custom Providers Section */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Custom Providers</h2>
          <p className="text-sm text-muted-foreground">
            Add OpenAI-compatible API endpoints to use with Pilot Space.
          </p>

          {/* Existing custom provider cards */}
          {customProviders.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {customProviders.map((p, idx) => (
                <ProviderStatusCard
                  key={`${p.provider}-${idx}`}
                  provider="custom"
                  isKeySet={p.isConfigured}
                  lastValidated={p.lastValidatedAt}
                  status={p.isValid ? 'connected' : 'unknown'}
                />
              ))}
            </div>
          )}

          <CustomProviderForm workspaceId={workspaceId} onSuccess={handleCustomProviderSuccess} />
        </div>

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
