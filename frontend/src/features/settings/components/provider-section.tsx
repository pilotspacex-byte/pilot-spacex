/**
 * ProviderSection - Dropdown-based provider selection for a service type.
 *
 * Replaces the expandable ProviderRow pattern with a Select dropdown.
 * Shows status badge next to dropdown and config form below.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { CheckCircle2, XCircle, Circle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProviderConfigForm } from './provider-config-form';
import { useStore } from '@/stores';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';

const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  google: 'Google Gemini',
  anthropic: 'Anthropic',
  ollama: 'Ollama',
};

export function StatusBadge({ status }: { status: WorkspaceAISettingsProvider | undefined }) {
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

export interface ProviderSectionProps {
  serviceType: 'embedding' | 'llm';
  icon: React.ElementType;
  title: string;
  description: string;
  onSaved: () => void;
}

export const ProviderSection = observer(function ProviderSection({
  serviceType,
  icon: Icon,
  title,
  description,
  onSaved,
}: ProviderSectionProps) {
  const { ai } = useStore();
  const { settings } = ai;
  const providers = settings.getProvidersByService(serviceType);

  // Use persisted default provider for this service type
  const storedDefault = settings.getDefaultProvider(serviceType);
  const fallback = providers[0]?.provider ?? '';
  const resolvedDefault = providers.some((p) => p.provider === storedDefault)
    ? storedDefault
    : fallback;

  const [selectedProvider, setSelectedProvider] = React.useState(resolvedDefault);

  // Sync when settings load/change
  React.useEffect(() => {
    if (resolvedDefault && selectedProvider !== resolvedDefault) {
      setSelectedProvider(resolvedDefault);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedDefault]);

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    // Local-only — persisted atomically when user clicks Save in the form
  };

  const selectedStatus = providers.find((p) => p.provider === selectedProvider);

  if (providers.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg font-medium">{title}</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Select value={selectedProvider} onValueChange={handleProviderChange}>
            <SelectTrigger className="w-[240px]">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {providers.map((p) => (
                <SelectItem key={p.provider} value={p.provider}>
                  {PROVIDER_DISPLAY_NAMES[p.provider] ?? p.provider}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <StatusBadge status={selectedStatus} />
        </div>

        {selectedProvider && (
          <ProviderConfigForm
            key={`${selectedProvider}-${serviceType}`}
            provider={selectedProvider}
            serviceType={serviceType}
            status={selectedStatus}
            setAsDefault
            onSaved={onSaved}
          />
        )}
      </CardContent>
    </Card>
  );
});
