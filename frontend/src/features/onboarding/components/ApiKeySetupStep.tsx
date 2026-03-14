'use client';

/**
 * ApiKeySetupStep - Inline API key setup for both AI services.
 *
 * ONBD-03: Inline API key setup within the onboarding checklist dialog.
 * Guides users to configure both required services:
 * 1. Anthropic (AI LLM Service)
 * 2. Google Gemini (Embedding Service)
 */
import { useState } from 'react';
import { Loader2, ExternalLink, CheckCircle2, BrainCircuit, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useValidateProviderKey } from '../hooks/useOnboardingActions';
import type { AIProviderType } from '@/services/api/onboarding';

interface ApiKeySetupStepProps {
  workspaceId: string;
  workspaceSlug: string;
  onNavigateToSettings: () => void;
}

interface ProviderKeyInputProps {
  provider: AIProviderType;
  label: string;
  icon: React.ReactNode;
  placeholder: string;
  hint: React.ReactNode;
  workspaceId: string;
}

function ProviderKeyInput({
  provider,
  label,
  icon,
  placeholder,
  hint,
  workspaceId,
}: ProviderKeyInputProps) {
  const [apiKey, setApiKey] = useState('');
  const { mutate: validateKey, isPending, data } = useValidateProviderKey({ workspaceId });

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {icon}
        <p className="text-xs font-medium text-foreground">{label}</p>
        {data?.valid && <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />}
      </div>
      <div className="text-xs text-muted-foreground">{hint}</div>
      <div className="space-y-2">
        <Label htmlFor={`${provider}-key-input`} className="sr-only">
          {label}
        </Label>
        <Input
          id={`${provider}-key-input`}
          type="password"
          placeholder={placeholder}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="h-8 text-sm font-mono"
        />
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={!apiKey.trim() || isPending}
          onClick={() => validateKey({ provider, apiKey: apiKey.trim() })}
        >
          {isPending && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
          Test connection
        </Button>
        {data?.valid && (
          <span className="text-xs text-green-600 font-medium">
            Connected &mdash; {data.modelsAvailable.length} model
            {data.modelsAvailable.length !== 1 ? 's' : ''}
          </span>
        )}
        {data && !data.valid && (
          <span className="text-xs text-destructive">{data.errorMessage ?? 'Invalid key'}</span>
        )}
      </div>
    </div>
  );
}

export function ApiKeySetupStep({ workspaceId, onNavigateToSettings }: ApiKeySetupStepProps) {
  return (
    <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-4 space-y-4">
      {/* Anthropic - AI LLM Service */}
      <ProviderKeyInput
        provider="anthropic"
        label="Anthropic (AI LLM)"
        icon={<BrainCircuit className="h-3.5 w-3.5 text-orange-600" />}
        placeholder="sk-ant-..."
        workspaceId={workspaceId}
        hint={
          <>
            Keys start with <code className="font-mono bg-muted px-1 rounded">sk-ant-</code>.{' '}
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-primary underline-offset-2 hover:underline"
            >
              Get your key
              <ExternalLink className="h-2.5 w-2.5" />
            </a>
          </>
        }
      />

      <div className="border-t border-border/40" />

      {/* Google Gemini - Embedding Service */}
      <ProviderKeyInput
        provider="google"
        label="Google Gemini (Embedding)"
        icon={<Database className="h-3.5 w-3.5 text-blue-600" />}
        placeholder="AIza..."
        workspaceId={workspaceId}
        hint={
          <>
            Keys start with <code className="font-mono bg-muted px-1 rounded">AIza</code>.{' '}
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-primary underline-offset-2 hover:underline"
            >
              Get your key
              <ExternalLink className="h-2.5 w-2.5" />
            </a>
          </>
        }
      />

      {/* Fallback link to full settings */}
      <div className="pt-1 border-t border-border/40">
        <button
          type="button"
          onClick={onNavigateToSettings}
          className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
        >
          Open full settings to save your keys
        </button>
      </div>
    </div>
  );
}
