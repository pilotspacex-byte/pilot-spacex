/**
 * AISettingsPage - Workspace AI configuration.
 *
 * T178: Main settings page with API keys, feature toggles, provider status.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Sparkles } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { APIKeyForm } from '../components/api-key-form';
import { AIFeatureToggles } from '../components/ai-feature-toggles';
import { ProviderStatusCard } from '../components/provider-status-card';
import { useStore } from '@/stores';

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
  const { ai } = useStore();
  const { settings } = ai;
  const params = useParams();
  const workspaceId = params?.workspaceSlug as string;

  React.useEffect(() => {
    if (workspaceId) {
      settings.loadSettings(workspaceId);
    }
  }, [workspaceId, settings]);

  if (settings.isLoading) {
    return (
      <div className="container max-w-4xl py-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (settings.error && !settings.settings) {
    return (
      <div className="container max-w-4xl py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load settings</AlertTitle>
          <AlertDescription>{settings.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container max-w-4xl py-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight">AI Settings</h1>
          </div>
          <p className="text-muted-foreground">
            Configure AI provider API keys and manage AI-powered features for your workspace.
          </p>
        </div>

        <Separator />

        {/* Provider Status Cards */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Provider Status</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <ProviderStatusCard
              provider="anthropic"
              isKeySet={settings.anthropicKeySet}
              lastValidated={
                settings.settings?.provider_status?.find((p) => p.provider === 'anthropic')
                  ?.last_validated_at
              }
              status={
                settings.settings?.provider_status?.find((p) => p.provider === 'anthropic')
                  ?.status ?? 'unknown'
              }
            />
            <ProviderStatusCard
              provider="openai"
              isKeySet={settings.openaiKeySet}
              lastValidated={
                settings.settings?.provider_status?.find((p) => p.provider === 'openai')
                  ?.last_validated_at
              }
              status={
                settings.settings?.provider_status?.find((p) => p.provider === 'openai')?.status ??
                'unknown'
              }
            />
          </div>
        </div>

        <Separator />

        {/* API Key Configuration */}
        <APIKeyForm />

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
