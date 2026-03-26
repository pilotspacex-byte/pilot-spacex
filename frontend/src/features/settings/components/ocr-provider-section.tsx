/**
 * OcrProviderSection - Document OCR provider configuration.
 *
 * Supports HunyuanOCR Self-Hosted (vLLM endpoint) and Tencent Cloud OCR.
 * Mirrors the Card > CardHeader > CardContent structure from provider-section.tsx.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, ScanText, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { StatusBadge } from './provider-section';
import {
  getOcrSettings,
  updateOcrSettings,
  testOcrConnection,
  type OcrSettingsResponse,
  type OcrConnectionTestResult,
} from '@/services/api/ocr';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';

const REGION_OPTIONS = [
  { value: 'ap-guangzhou', label: 'Asia Pacific — Guangzhou' },
  { value: 'ap-beijing', label: 'Asia Pacific — Beijing' },
  { value: 'ap-shanghai', label: 'Asia Pacific — Shanghai' },
  { value: 'ap-singapore', label: 'Asia Pacific — Singapore' },
];

/** Convert OcrSettingsResponse to the StatusBadge-compatible shape. */
function toProviderStatus(
  settings: OcrSettingsResponse | null
): WorkspaceAISettingsProvider | undefined {
  if (!settings || settings.provider_type === 'none') return undefined;
  return {
    provider: settings.provider_type,
    serviceType: 'llm',
    isConfigured: settings.is_configured,
    isValid: settings.is_valid,
    lastValidatedAt: null,
  };
}

export interface OcrProviderSectionProps {
  workspaceId: string;
  onSaved: () => void;
}

export const OcrProviderSection = observer(function OcrProviderSection({
  workspaceId,
  onSaved,
}: OcrProviderSectionProps) {
  const [settings, setSettings] = React.useState<OcrSettingsResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isTesting, setIsTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState<OcrConnectionTestResult | null>(null);

  // HunyuanOCR fields
  const [endpointUrl, setEndpointUrl] = React.useState('');
  const [apiKey, setApiKey] = React.useState('');

  // Tencent Cloud fields
  const [secretId, setSecretId] = React.useState('');
  const [secretKey, setSecretKey] = React.useState('');
  const [region, setRegion] = React.useState('ap-guangzhou');

  // Provider type selection
  const [selectedType, setSelectedType] = React.useState<'none' | 'hunyuan_ocr' | 'tencent_ocr'>(
    'none'
  );

  React.useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;

    setIsLoading(true);
    getOcrSettings(workspaceId)
      .then((data) => {
        if (cancelled) return;
        setSettings(data);
        setSelectedType(data.provider_type);
        if (data.provider_type === 'hunyuan_ocr') {
          setEndpointUrl(data.endpoint_url ?? '');
        }
      })
      .catch(() => {
        if (cancelled) return;
        // Non-fatal: show unconfigured state
      })
      .finally(() => {
        if (cancelled) return;
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  const handleTypeChange = (value: string) => {
    setSelectedType(value as 'none' | 'hunyuan_ocr' | 'tencent_ocr');
    setTestResult(null);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setTestResult(null);
    try {
      const payload: Parameters<typeof updateOcrSettings>[1] = {
        provider_type: selectedType,
      };

      if (selectedType === 'hunyuan_ocr') {
        if (!endpointUrl.trim()) {
          toast.error('Endpoint URL is required for HunyuanOCR');
          return;
        }
        payload.endpoint_url = endpointUrl.trim();
        if (apiKey.trim()) payload.api_key = apiKey.trim();
      } else if (selectedType === 'tencent_ocr') {
        if (!secretId.trim() || !secretKey.trim()) {
          toast.error('Secret ID and Secret Key are required for Tencent Cloud OCR');
          return;
        }
        payload.secret_id = secretId.trim();
        payload.secret_key = secretKey.trim();
        payload.region = region;
      }

      const updated = await updateOcrSettings(workspaceId, payload);
      setSettings(updated);
      setApiKey('');
      setSecretKey('');
      toast.success('OCR settings saved');
      onSaved();
    } catch (error) {
      toast.error('Failed to save OCR settings', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const testPayload: Parameters<typeof testOcrConnection>[1] = {
        provider_type: selectedType,
      };
      if (selectedType === 'hunyuan_ocr') {
        testPayload.endpoint_url = endpointUrl.trim();
        if (apiKey.trim()) testPayload.api_key = apiKey.trim();
        testPayload.model_name = settings?.model_name || undefined;
      } else if (selectedType === 'tencent_ocr') {
        testPayload.secret_id = secretId.trim();
        testPayload.secret_key = secretKey.trim();
        testPayload.region = region;
      }
      const result = await testOcrConnection(workspaceId, testPayload);
      setTestResult(result);
      if (result.success) {
        toast.success('OCR connection successful');
      } else {
        toast.error('OCR connection failed', { description: result.error ?? undefined });
      }
    } catch (error) {
      toast.error('Connection test failed', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setIsTesting(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-4">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-80" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-60" />
        </CardContent>
      </Card>
    );
  }

  const providerStatus = toProviderStatus(settings);

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <ScanText className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg font-medium">Document OCR</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure a dedicated OCR provider for extracting text from scanned PDFs and images.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Provider type selector + status badge */}
        <div className="flex items-center gap-3">
          <Select value={selectedType} onValueChange={handleTypeChange}>
            <SelectTrigger className="w-[240px]">
              <SelectValue placeholder="Select OCR provider" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None (use AI provider fallback)</SelectItem>
              <SelectItem value="hunyuan_ocr">HunyuanOCR Self-Hosted</SelectItem>
              <SelectItem value="tencent_ocr">Tencent Cloud OCR</SelectItem>
            </SelectContent>
          </Select>
          <StatusBadge status={providerStatus} />
        </div>

        {/* HunyuanOCR Self-Hosted config */}
        {selectedType === 'hunyuan_ocr' && (
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <div className="flex items-center gap-1.5">
                <Label htmlFor="ocr-endpoint-url">Endpoint URL</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      className="inline-flex items-center justify-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                      aria-label="Endpoint URL help"
                    >
                      <Info className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Requires 20GB VRAM. Deploy with: vllm serve tencent/HunyuanOCR
                  </TooltipContent>
                </Tooltip>
              </div>
              <Input
                id="ocr-endpoint-url"
                value={endpointUrl}
                onChange={(e) => setEndpointUrl(e.target.value)}
                placeholder="https://your-vllm-server:8000"
                disabled={isSaving}
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ocr-api-key">API Key (optional)</Label>
              <Input
                id="ocr-api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={settings?.is_configured ? '••••••••' : 'Leave blank if not required'}
                disabled={isSaving}
                autoComplete="new-password"
              />
            </div>
          </div>
        )}

        {/* Tencent Cloud OCR config */}
        {selectedType === 'tencent_ocr' && (
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="ocr-secret-id">Secret ID</Label>
              <Input
                id="ocr-secret-id"
                value={secretId}
                onChange={(e) => setSecretId(e.target.value)}
                placeholder={settings?.is_configured ? '••••••••' : 'Your Tencent Cloud Secret ID'}
                disabled={isSaving}
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ocr-secret-key">Secret Key</Label>
              <Input
                id="ocr-secret-key"
                type="password"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                placeholder={settings?.is_configured ? '••••••••' : 'Your Tencent Cloud Secret Key'}
                disabled={isSaving}
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ocr-region">Region</Label>
              <Select value={region} onValueChange={setRegion} disabled={isSaving}>
                <SelectTrigger id="ocr-region" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REGION_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {/* None — descriptive fallback text */}
        {selectedType === 'none' && (
          <p className="text-sm text-muted-foreground">
            OCR will use your configured AI provider (Claude/GPT-4o) for image and scanned PDF
            extraction.
          </p>
        )}

        {/* Test result alert */}
        {testResult && (
          <Alert
            variant={testResult.success ? 'default' : 'destructive'}
            className={
              testResult.success ? 'border-green-500/20 bg-green-500/10 text-green-700' : undefined
            }
          >
            <AlertDescription>
              {testResult.success
                ? `Connection successful. Extracted text: ${(testResult.extracted_text ?? '').slice(0, 200)}${(testResult.extracted_text ?? '').length > 200 ? '…' : ''}`
                : (testResult.error ?? 'Connection failed')}
            </AlertDescription>
          </Alert>
        )}

        {/* Action buttons */}
        <div className="flex items-center justify-between pt-2">
          <div>
            {settings?.is_configured && selectedType !== 'none' && (
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={isTesting || isSaving}
                className="min-w-[140px]"
              >
                {isTesting && <Loader2 className="h-4 w-4 animate-spin" />}
                {isTesting ? 'Testing...' : 'Test Connection'}
              </Button>
            )}
          </div>
          <Button onClick={handleSave} disabled={isSaving} className="min-w-[100px]">
            {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
});
