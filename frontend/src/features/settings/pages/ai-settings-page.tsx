/**
 * AISettingsPage - Workspace AI configuration.
 *
 * Two service sections: Embedding Service and AI LLM Service.
 * Supported providers: Google Gemini (embedding), Anthropic (llm), Ollama (both).
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Database, BrainCircuit } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { ProviderRow } from '../components/provider-row';
import { AIFeatureToggles } from '../components/ai-feature-toggles';
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

  const embeddingProviders = settings.getProvidersByService('embedding');
  const llmProviders = settings.getProvidersByService('llm');

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">AI Services</h1>
          <p className="text-sm text-muted-foreground">
            Configure the two AI services required for your workspace: Embedding and LLM.
          </p>
        </div>

        {/* Embedding Service Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Database className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-medium">Embedding Service</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-3">
            Used for semantic search, knowledge graph, and RAG. Configure one provider.
          </p>
          <div className="space-y-2">
            {embeddingProviders.map((p) => (
              <ProviderRow
                key={`${p.provider}-${p.serviceType}`}
                provider={p.provider}
                serviceType="embedding"
                status={p}
                workspaceId={workspaceId}
                onSaved={handleProviderSaved}
              />
            ))}
          </div>
        </section>

        <Separator />

        {/* AI LLM Service Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <BrainCircuit className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-medium">AI LLM Service</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-3">
            Used for AI agents, ghost text, PR review, and issue extraction. Anthropic-compatible
            API.
          </p>
          <div className="space-y-2">
            {llmProviders.map((p) => (
              <ProviderRow
                key={`${p.provider}-${p.serviceType}`}
                provider={p.provider}
                serviceType="llm"
                status={p}
                workspaceId={workspaceId}
                onSaved={handleProviderSaved}
              />
            ))}
          </div>
        </section>

        <Separator />

        {/* Feature Toggles */}
        <AIFeatureToggles />

        {/* Info Alert */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Security & Privacy</AlertTitle>
          <AlertDescription>
            API keys are encrypted at rest using Fernet encryption. Keys are never logged or exposed
            in responses. Each AI request is tracked for cost monitoring and audit purposes.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
});
