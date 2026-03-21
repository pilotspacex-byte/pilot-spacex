/**
 * AISettingsPage - Workspace AI provider configuration.
 *
 * Redesigned with:
 * - Setup progress indicator showing Embedding + LLM completion
 * - Tabbed provider panel (Embedding | LLM) to eliminate scrolling
 * - Feature toggles with clear inline guidance
 * - Consistent "AI Providers" naming (matches sidebar nav)
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Database, BrainCircuit, Mic, CheckCircle2, Circle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ProviderSection } from '../components/provider-section';
import { AIFeatureToggles } from '../components/ai-feature-toggles';
import { useStore } from '@/stores';
import { cn } from '@/lib/utils';

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-80" />
      </div>
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-[280px] w-full" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}

/** Compact setup progress showing Embedding + LLM status. */
const SetupProgress = observer(function SetupProgress() {
  const { ai } = useStore();
  const { settings } = ai;

  const embeddingProviders = settings.getProvidersByService('embedding');
  const llmProviders = settings.getProvidersByService('llm');

  const embeddingConfigured = embeddingProviders.some((p) => p.isConfigured);
  const llmConfigured = llmProviders.some((p) => p.isConfigured);
  const embeddingConnected = embeddingProviders.some((p) => p.isValid === true);
  const llmConnected = llmProviders.some((p) => p.isValid === true);

  const bothConfigured = embeddingConfigured && llmConfigured;

  if (bothConfigured && embeddingConnected && llmConnected) return null;

  const steps = [
    {
      label: 'LLM',
      done: llmConfigured,
      connected: llmConnected,
      icon: BrainCircuit,
    },
    {
      label: 'Embedding',
      done: embeddingConfigured,
      connected: embeddingConnected,
      icon: Database,
    },
  ];

  return (
    <div className="rounded-lg border border-border bg-background-subtle p-4">
      <p className="text-xs font-medium text-muted-foreground mb-3">Setup progress</p>
      <div className="flex items-center gap-6">
        {steps.map((step, i) => (
          <React.Fragment key={step.label}>
            {i > 0 && (
              <div
                className={cn(
                  'h-px flex-1 max-w-12 transition-colors',
                  step.done ? 'bg-primary' : 'bg-border'
                )}
              />
            )}
            <div className="flex items-center gap-2">
              {step.connected ? (
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
              ) : step.done ? (
                <CheckCircle2 className="h-4 w-4 text-muted-foreground shrink-0" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground/50 shrink-0" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  step.connected
                    ? 'text-primary'
                    : step.done
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                )}
              >
                {step.label}
              </span>
              {step.connected && <span className="text-xs text-primary">Connected</span>}
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
});

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

  const handleProviderSaved = React.useCallback(() => {
    settings.loadSettings(workspaceId);
    settings.loadModels(workspaceId);
  }, [workspaceId, settings]);

  if (settings.isLoading) {
    return (
      <div className="px-6 py-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (settings.error && !settings.settings) {
    return (
      <div className="px-6 py-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load settings</AlertTitle>
          <AlertDescription>{settings.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 lg:px-8">
      <div className="space-y-6">
        {/* Header — consistent with sidebar nav label */}
        <div className="space-y-1">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">AI Providers</h1>
          <p className="text-sm text-muted-foreground">
            Configure your Embedding and LLM providers for AI features.
          </p>
        </div>

        {/* Setup progress — hidden when fully connected */}
        <SetupProgress />

        {/* Tabbed provider panel */}
        <ProviderTabs onSaved={handleProviderSaved} />

        {/* Feature toggles */}
        <AIFeatureToggles />
      </div>
    </div>
  );
});

/** Tabbed panel for Embedding / LLM provider selection. */
const ProviderTabs = observer(function ProviderTabs({ onSaved }: { onSaved: () => void }) {
  const { ai } = useStore();
  const { settings } = ai;

  const embeddingProviders = settings.getProvidersByService('embedding');
  const llmProviders = settings.getProvidersByService('llm');
  const sttProviders = settings.getProvidersByService('stt');

  const embeddingConnected = embeddingProviders.some((p) => p.isValid === true);
  const llmConnected = llmProviders.some((p) => p.isValid === true);
  const sttConnected = sttProviders.some((p) => p.isValid === true);

  // Default to LLM tab (primary service)
  const defaultTab = 'llm';

  return (
    <Tabs defaultValue={defaultTab} className="w-full">
      <TabsList variant="line" className="w-full justify-start border-b border-border pb-0">
        <TabsTrigger value="llm" className="gap-2 px-4">
          <BrainCircuit className="h-3.5 w-3.5" />
          LLM
          {llmConnected && <CheckCircle2 className="h-3 w-3 text-primary" />}
        </TabsTrigger>
        <TabsTrigger value="embedding" className="gap-2 px-4">
          <Database className="h-3.5 w-3.5" />
          Embedding
          {embeddingConnected && <CheckCircle2 className="h-3 w-3 text-primary" />}
        </TabsTrigger>
        <TabsTrigger value="stt" className="gap-2 px-4">
          <Mic className="h-3.5 w-3.5" />
          Voice
          {sttConnected && <CheckCircle2 className="h-3 w-3 text-primary" />}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="llm" className="mt-4">
        <ProviderSection
          serviceType="llm"
          description="Used for AI agents, ghost text, PR review, and issue extraction."
          onSaved={onSaved}
        />
      </TabsContent>

      <TabsContent value="embedding" className="mt-4">
        <ProviderSection
          serviceType="embedding"
          description="Used for semantic search, knowledge graph, and RAG."
          onSaved={onSaved}
        />
      </TabsContent>

      <TabsContent value="stt" className="mt-4">
        <ProviderSection
          serviceType="stt"
          description="Used for voice-to-text transcription in AI Chat."
          onSaved={onSaved}
        />
      </TabsContent>
    </Tabs>
  );
});
