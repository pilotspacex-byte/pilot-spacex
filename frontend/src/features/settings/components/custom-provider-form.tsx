/**
 * CustomProviderForm - Register a custom OpenAI-compatible AI provider.
 *
 * 13-03: AIPR-05 — user can add custom providers (name + base URL + API key).
 */

'use client';

import * as React from 'react';
import { Loader2, AlertCircle, PlusCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/services/api/client';
import { toast } from 'sonner';

interface CustomProviderFormProps {
  workspaceId: string;
  onSuccess: () => void;
}

export function CustomProviderForm({ workspaceId, onSuccess }: CustomProviderFormProps) {
  const [displayName, setDisplayName] = React.useState('');
  const [baseUrl, setBaseUrl] = React.useState('');
  const [apiKey, setApiKey] = React.useState('');
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const canSubmit =
    displayName.trim().length > 0 && baseUrl.trim().length > 0 && apiKey.trim().length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.post('/ai/configurations', {
        provider: 'custom',
        display_name: displayName.trim(),
        base_url: baseUrl.trim(),
        api_key: apiKey.trim(),
        workspace_id: workspaceId,
      });

      toast.success('Custom provider added');
      setDisplayName('');
      setBaseUrl('');
      setApiKey('');
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add provider');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <PlusCircle className="h-5 w-5 text-primary" />
          <CardTitle>Add Custom Provider</CardTitle>
        </div>
        <CardDescription>
          Register an OpenAI-compatible API endpoint. Supports any provider that follows the OpenAI
          chat completions API format.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="custom-provider-name">Display Name</Label>
            <Input
              id="custom-provider-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="My LLM Provider"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="custom-provider-url">Base URL</Label>
            <Input
              id="custom-provider-url"
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.example.com/v1"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="custom-provider-key">API Key</Label>
            <Input
              id="custom-provider-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              disabled={isSubmitting}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button type="submit" disabled={!canSubmit || isSubmitting} className="w-full">
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isSubmitting ? 'Adding...' : 'Add Provider'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
