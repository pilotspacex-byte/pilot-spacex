/**
 * ProviderRow - Expandable provider configuration row.
 *
 * Supports 3 providers: Google Gemini, Anthropic, Ollama.
 * Shows "Supports Embedding + LLM" badge for providers that handle both services.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  Cpu,
  Sparkles,
  CheckCircle2,
  XCircle,
  Circle,
} from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { APIKeyInput } from './api-key-input';
import { useStore } from '@/stores';
import { toast } from 'sonner';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';
import { formatDistanceToNow } from 'date-fns';

interface ProviderConfig {
  name: string;
  fields: ('api_key' | 'base_url' | 'model_name')[];
  iconColor: string;
  apiKeyOptional?: boolean;
  baseUrlRequired?: boolean;
  baseUrlPlaceholder?: string;
  modelPlaceholder?: string;
}

const PROVIDER_CONFIG: Record<string, ProviderConfig> = {
  google: {
    name: 'Google Gemini',
    fields: ['api_key', 'base_url'],
    iconColor: 'blue',
    baseUrlPlaceholder: 'https://generativelanguage.googleapis.com (optional)',
  },
  anthropic: {
    name: 'Anthropic',
    fields: ['api_key', 'base_url'],
    iconColor: 'orange',
    baseUrlPlaceholder: 'https://api.anthropic.com (optional)',
  },
  ollama: {
    name: 'Ollama',
    fields: ['base_url', 'model_name', 'api_key'],
    iconColor: 'purple',
    apiKeyOptional: true,
    baseUrlRequired: true,
    baseUrlPlaceholder: 'http://localhost:11434',
    modelPlaceholder: 'e.g. nomic-embed-text, qwen2.5',
  },
};

const ICON_COLOR_CLASSES: Record<string, string> = {
  orange: 'bg-orange-500/10 text-orange-600',
  blue: 'bg-blue-500/10 text-blue-600',
  purple: 'bg-purple-500/10 text-purple-600',
};

function ProviderIcon({ provider, iconColor }: { provider: string; iconColor: string }) {
  const colorClass = ICON_COLOR_CLASSES[iconColor] ?? 'bg-muted text-muted-foreground';

  if (provider === 'anthropic') {
    return (
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-lg ${colorClass}`}
        aria-hidden="true"
      >
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
        </svg>
      </div>
    );
  }

  if (provider === 'google') {
    return (
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-lg ${colorClass}`}
        aria-hidden="true"
      >
        <Sparkles className="h-5 w-5" />
      </div>
    );
  }

  return (
    <div
      className={`flex h-10 w-10 items-center justify-center rounded-lg ${colorClass}`}
      aria-hidden="true"
    >
      <Cpu className="h-5 w-5" />
    </div>
  );
}

function StatusBadge({ status }: { status: WorkspaceAISettingsProvider | undefined }) {
  if (!status || !status.isConfigured) {
    return (
      <Badge variant="outline" className="gap-1.5">
        <Circle className="h-3 w-3 fill-muted-foreground text-muted-foreground" />
        Not configured
      </Badge>
    );
  }

  if (status.isValid === true) {
    return (
      <Badge
        variant="outline"
        className="gap-1.5 border-green-500/20 bg-green-500/10 text-green-600"
      >
        <CheckCircle2 className="h-3 w-3" />
        Connected
      </Badge>
    );
  }

  if (status.isValid === false) {
    return (
      <Badge
        variant="outline"
        className="gap-1.5 border-destructive/20 bg-destructive/10 text-destructive"
      >
        <XCircle className="h-3 w-3" />
        Failed
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="gap-1.5">
      <Circle className="h-3 w-3" />
      Configured
    </Badge>
  );
}

function getSubtitle(status: WorkspaceAISettingsProvider | undefined): string {
  if (!status || !status.isConfigured) return 'Not configured';
  if (!status.lastValidatedAt) return 'Not validated yet';
  try {
    return `Last validated ${formatDistanceToNow(new Date(status.lastValidatedAt), { addSuffix: true })}`;
  } catch {
    return 'Last validated recently';
  }
}

export interface ProviderRowProps {
  provider: string;
  serviceType: 'embedding' | 'llm';
  status: WorkspaceAISettingsProvider | undefined;
  onSaved: () => void;
}

export const ProviderRow = observer(function ProviderRow({
  provider,
  serviceType,
  status,
  onSaved,
}: ProviderRowProps) {
  const { ai } = useStore();
  const { settings } = ai;
  const config = PROVIDER_CONFIG[provider];

  const [isOpen, setIsOpen] = React.useState(false);
  const [apiKey, setApiKey] = React.useState('');
  const [baseUrl, setBaseUrl] = React.useState(status?.baseUrl ?? '');
  const [modelName, setModelName] = React.useState(status?.modelName ?? '');
  const [isSaving, setIsSaving] = React.useState(false);

  if (!config) return null;

  const handleSave = async () => {
    const entry: {
      provider: string;
      service_type: 'embedding' | 'llm';
      api_key?: string;
      base_url?: string;
      model_name?: string;
    } = { provider, service_type: serviceType };

    const hasApiKey = apiKey.trim().length > 0;
    if (hasApiKey) entry.api_key = apiKey.trim();

    const hasBaseUrl = baseUrl.trim().length > 0;
    const hasModelName = modelName.trim().length > 0;
    if (hasBaseUrl) entry.base_url = baseUrl.trim();
    if (hasModelName) entry.model_name = modelName.trim();

    // Validate required fields
    if (config.baseUrlRequired && !hasBaseUrl && !status?.baseUrl) {
      toast.error('Base URL is required for this provider');
      return;
    }

    if (!hasApiKey && !hasBaseUrl && !hasModelName) {
      toast.info('No changes to save');
      return;
    }

    setIsSaving(true);
    try {
      await settings.saveSettings({ api_keys: [entry] });
      toast.success(`${config.name} settings saved`);
      setApiKey('');
      setBaseUrl('');
      setModelName('');
      setIsOpen(false);
      onSaved();
    } catch (error) {
      toast.error(`Failed to save ${config.name} settings`, {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full cursor-pointer items-center justify-between p-4 hover:bg-muted/30 transition-colors text-left"
            aria-expanded={isOpen}
            aria-label={`Configure ${config.name}`}
          >
            <div className="flex items-center gap-3">
              <ProviderIcon provider={provider} iconColor={config.iconColor} />
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">{config.name}</p>
                </div>
                <p className="text-xs text-muted-foreground">{getSubtitle(status)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={status} />
              {isOpen ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t px-4 pb-4 pt-4 space-y-4">
            {config.fields.includes('base_url') && (
              <div className="space-y-2">
                <Label htmlFor={`${provider}-${serviceType}-base-url`}>
                  Base URL{config.baseUrlRequired ? '' : ' (optional)'}
                </Label>
                <Input
                  id={`${provider}-${serviceType}-base-url`}
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder={
                    status?.baseUrl ?? config.baseUrlPlaceholder ?? 'https://api.example.com/v1'
                  }
                  disabled={isSaving}
                  autoComplete="off"
                />
              </div>
            )}

            {config.fields.includes('model_name') && (
              <div className="space-y-2">
                <Label htmlFor={`${provider}-${serviceType}-model-name`}>Model Name</Label>
                <Input
                  id={`${provider}-${serviceType}-model-name`}
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder={status?.modelName ?? config.modelPlaceholder ?? 'Model name'}
                  disabled={isSaving}
                  autoComplete="off"
                />
              </div>
            )}

            {config.fields.includes('api_key') && (
              <APIKeyInput
                label={config.apiKeyOptional ? 'API Key (optional)' : 'API Key'}
                value={apiKey}
                onChange={setApiKey}
                isSet={!config.apiKeyOptional && (status?.isConfigured ?? false)}
                provider={provider}
                disabled={isSaving}
              />
            )}

            <div className="flex justify-end pt-2">
              <Button onClick={handleSave} disabled={isSaving} className="min-w-[100px]">
                {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
});
