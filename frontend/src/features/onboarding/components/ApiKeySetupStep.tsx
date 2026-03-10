'use client';

/**
 * ApiKeySetupStep - Inline API key guidance component for onboarding.
 *
 * ONBD-03: Inline API key setup within the onboarding checklist dialog.
 * Replaces the navigate-away behaviour for the ai_providers step.
 * Source: FR-005, FR-006, US1
 */
import { useState } from 'react';
import { Loader2, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useValidateProviderKey } from '../hooks/useOnboardingActions';

interface ApiKeySetupStepProps {
  /** Workspace ID (UUID) */
  workspaceId: string;
  /** Workspace slug for fallback navigation */
  workspaceSlug: string;
  /** Fallback: navigate to full AI providers settings page */
  onNavigateToSettings: () => void;
}

/**
 * ApiKeySetupStep - Inline Anthropic API key input, format hint, and connection test.
 *
 * Rendered below the ai_providers checklist item when it is active.
 * Does NOT navigate away; shows success/error inline.
 */
export function ApiKeySetupStep({ workspaceId, onNavigateToSettings }: ApiKeySetupStepProps) {
  const [apiKey, setApiKey] = useState('');
  const { mutate: validateKey, isPending, data } = useValidateProviderKey({ workspaceId });

  return (
    <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-4 space-y-3">
      {/* Format hint + console link */}
      <div className="space-y-1">
        <p className="text-xs font-medium text-foreground">Anthropic API Key</p>
        <p className="text-xs text-muted-foreground">
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
        </p>
      </div>

      {/* API key input */}
      <div className="space-y-2">
        <Label htmlFor="api-key-input" className="text-xs">
          API key
        </Label>
        <Input
          id="api-key-input"
          type="password"
          placeholder="sk-ant-..."
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="h-8 text-sm font-mono"
        />
      </div>

      {/* Test connection button + inline result */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={!apiKey.trim() || isPending}
          onClick={() => validateKey({ provider: 'anthropic', apiKey: apiKey.trim() })}
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

      {/* Fallback link to full settings */}
      <div className="pt-1 border-t border-border/40">
        <button
          type="button"
          onClick={onNavigateToSettings}
          className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
        >
          Open full settings to save your key
        </button>
      </div>
    </div>
  );
}
