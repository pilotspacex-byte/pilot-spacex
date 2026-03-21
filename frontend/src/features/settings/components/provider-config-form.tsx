/**
 * ProviderConfigForm - Configuration form for a single AI provider.
 *
 * Renders base_url, model_name, and api_key fields based on provider config.
 * Inline security note next to API key label. Handles save with toast feedback.
 */

'use client';

import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { APIKeyInput } from './api-key-input';
import { useStore } from '@/stores';
import { toast } from 'sonner';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';

interface ProviderFieldConfig {
  name: string;
  fields: ('api_key' | 'base_url' | 'model_name')[];
  apiKeyOptional?: boolean;
  baseUrlRequired?: boolean;
  baseUrlPlaceholder?: string;
  modelPlaceholder?: string;
}

const PROVIDER_CONFIG: Record<string, ProviderFieldConfig> = {
  google: {
    name: 'Google Gemini',
    fields: ['api_key', 'base_url'],
    baseUrlPlaceholder: 'https://generativelanguage.googleapis.com (optional)',
  },
  anthropic: {
    name: 'Anthropic',
    fields: ['api_key', 'base_url'],
    baseUrlPlaceholder: 'https://api.anthropic.com (optional)',
  },
  ollama: {
    name: 'Ollama',
    fields: ['base_url', 'model_name', 'api_key'],
    apiKeyOptional: true,
    baseUrlRequired: true,
    baseUrlPlaceholder: 'http://localhost:11434',
    modelPlaceholder: 'e.g. nomic-embed-text, qwen2.5',
  },
  elevenlabs: {
    name: 'ElevenLabs',
    fields: ['api_key'],
    // No base_url or model_name — ElevenLabs uses fixed endpoint
  },
};

/** Resolve model placeholder based on provider + service type. */
function getModelPlaceholder(
  provider: string,
  serviceType: 'embedding' | 'llm' | 'stt',
  config: ProviderFieldConfig
): string {
  if (provider === 'ollama' && serviceType === 'embedding') {
    return 'nomic-embed-text-v2-moe';
  }
  if (provider === 'ollama' && serviceType === 'llm') {
    return 'qwen2.5';
  }
  return config.modelPlaceholder ?? 'Model name';
}

export interface ProviderConfigFormProps {
  provider: string;
  serviceType: 'embedding' | 'llm' | 'stt';
  status: WorkspaceAISettingsProvider | undefined;
  /** When true, saving also sets this provider as the active default for its service type. */
  setAsDefault?: boolean;
  onSaved: () => void;
}

export function ProviderConfigForm({
  provider,
  serviceType,
  status,
  setAsDefault,
  onSaved,
}: ProviderConfigFormProps) {
  const { ai } = useStore();
  const { settings } = ai;
  const config = PROVIDER_CONFIG[provider];

  const [apiKey, setApiKey] = React.useState('');
  const [baseUrl, setBaseUrl] = React.useState(status?.baseUrl ?? '');
  const [modelName, setModelName] = React.useState(status?.modelName ?? '');
  const [isSaving, setIsSaving] = React.useState(false);

  // Reset fields when provider or status changes
  React.useEffect(() => {
    setApiKey('');
    setBaseUrl(status?.baseUrl ?? '');
    setModelName(status?.modelName ?? '');
  }, [provider, status?.baseUrl, status?.modelName]);

  if (!config) return null;

  const modelPlaceholder = getModelPlaceholder(provider, serviceType, config);

  const handleSave = async () => {
    const entry: {
      provider: string;
      service_type: 'embedding' | 'llm' | 'stt';
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
      // Include default provider selection atomically with the config save
      const saveData: Parameters<typeof settings.saveSettings>[0] = { api_keys: [entry] };
      if (setAsDefault) {
        if (serviceType === 'llm') {
          saveData.default_llm_provider = provider;
        } else if (serviceType === 'embedding') {
          saveData.default_embedding_provider = provider;
        }
        // 'stt' providers do not have a default_* field (only one stt provider: elevenlabs)
      }
      await settings.saveSettings(saveData);
      // Check for validation warnings (saved but validation failed, e.g. Ollama not running)
      const providerLabel = `${provider}:${serviceType}`;
      const validationWarning = settings.validationErrors[providerLabel];
      if (validationWarning) {
        toast.warning(`${config.name} saved with warning`, {
          description: validationWarning,
        });
      } else {
        toast.success(`${config.name} settings saved`);
      }
      setApiKey('');
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
    <div className="space-y-4 rounded-lg border border-border bg-background p-4">
      {config.fields.includes('base_url') && (
        <div className="space-y-2">
          <Label htmlFor={`${provider}-${serviceType}-base-url`}>
            Base URL{config.baseUrlRequired ? '' : ' (optional)'}
          </Label>
          <Input
            id={`${provider}-${serviceType}-base-url`}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={config.baseUrlPlaceholder ?? 'https://api.example.com/v1'}
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
            placeholder={modelPlaceholder}
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

      <div className="flex items-center justify-between pt-1">
        <p className="text-xs text-muted-foreground/70">
          Keys are encrypted at rest and never logged.
        </p>
        <Button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          size="sm"
          className="min-w-[88px]"
        >
          {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
