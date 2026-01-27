/**
 * APIKeyForm - Form for managing workspace API keys.
 *
 * T179: API key inputs for Anthropic (required) and OpenAI (required for search).
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, AlertCircle, Info, Key } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { APIKeyInput } from './api-key-input';
import { useStore } from '@/stores';
import { toast } from 'sonner';

export const APIKeyForm = observer(function APIKeyForm() {
  const { ai } = useStore();
  const { settings } = ai;

  const [anthropicKey, setAnthropicKey] = React.useState('');
  const [openaiKey, setOpenaiKey] = React.useState('');
  const [validationErrors, setValidationErrors] = React.useState<{
    anthropic?: string;
    openai?: string;
  }>({});

  const validateKey = (provider: 'anthropic' | 'openai', key: string): string | undefined => {
    if (!key) return undefined; // Empty is valid (means no change)

    if (key.length < 10) {
      return 'API key is too short';
    }

    if (provider === 'anthropic' && !key.startsWith('sk-ant-')) {
      return 'Anthropic API keys must start with "sk-ant-"';
    }

    if (provider === 'openai' && !key.startsWith('sk-')) {
      return 'OpenAI API keys must start with "sk-"';
    }

    return undefined;
  };

  const handleSave = async () => {
    // Client-side validation
    const errors: typeof validationErrors = {};
    const anthropicError = validateKey('anthropic', anthropicKey);
    const openaiError = validateKey('openai', openaiKey);

    if (anthropicError) errors.anthropic = anthropicError;
    if (openaiError) errors.openai = openaiError;

    setValidationErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    // Only send non-empty keys (unchanged keys remain empty)
    const updates: {
      anthropic_api_key?: string;
      openai_api_key?: string;
    } = {};

    if (anthropicKey) updates.anthropic_api_key = anthropicKey;
    if (openaiKey) updates.openai_api_key = openaiKey;

    if (Object.keys(updates).length === 0) {
      toast.info('No changes to save');
      return;
    }

    try {
      await settings.saveSettings(updates);

      // Clear input fields after successful save
      setAnthropicKey('');
      setOpenaiKey('');
      setValidationErrors({});

      toast.success('API keys saved securely');
    } catch (error) {
      toast.error('Failed to save API keys', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    }
  };

  const hasChanges = anthropicKey.length > 0 || openaiKey.length > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary" />
          <CardTitle>API Keys</CardTitle>
        </div>
        <CardDescription>
          Configure your AI provider API keys. Keys are encrypted and stored securely in Supabase
          Vault.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Both Anthropic and OpenAI API keys are required for full functionality. Anthropic powers
            code generation, and OpenAI provides semantic search.
          </AlertDescription>
        </Alert>

        <div className="space-y-4">
          <APIKeyInput
            label="Anthropic API Key"
            value={anthropicKey}
            onChange={setAnthropicKey}
            isSet={settings.anthropicKeySet}
            required
            error={validationErrors.anthropic}
            disabled={settings.isSaving}
            provider="anthropic"
            placeholder={settings.anthropicKeySet ? '••••••••••••••••••••' : 'sk-ant-...'}
          />

          <Separator />

          <APIKeyInput
            label="OpenAI API Key"
            value={openaiKey}
            onChange={setOpenaiKey}
            isSet={settings.openaiKeySet}
            required
            error={validationErrors.openai}
            disabled={settings.isSaving}
            provider="openai"
            placeholder={settings.openaiKeySet ? '••••••••••••••••••••' : 'sk-...'}
          />
        </div>

        {settings.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{settings.error}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-muted-foreground">
            {hasChanges ? 'You have unsaved changes' : 'No pending changes'}
          </p>
          <Button
            onClick={handleSave}
            disabled={settings.isSaving || !hasChanges}
            className="min-w-[120px]"
          >
            {settings.isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
            {settings.isSaving ? 'Saving...' : 'Save Keys'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
});
