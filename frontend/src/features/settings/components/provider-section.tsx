/**
 * ProviderSection - Provider selection and configuration for a service type.
 *
 * Renders inside a tab panel. Shows provider dropdown with brand icons,
 * status badge, and inline config form.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { CheckCircle2, XCircle, Circle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProviderConfigForm } from './provider-config-form';
import { ProviderIcon } from './provider-icons';
import { useStore } from '@/stores';
import type { WorkspaceAISettingsProvider } from '@/services/api/ai';

const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  google: 'Google Gemini',
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  ollama: 'Ollama',
  elevenlabs: 'ElevenLabs',
};

export function StatusBadge({ status }: { status: WorkspaceAISettingsProvider | undefined }) {
  if (!status || !status.isConfigured) {
    return (
      <Badge variant="outline" className="gap-1.5 text-muted-foreground">
        <Circle className="h-3 w-3 fill-muted-foreground/50 text-muted-foreground/50" />
        Not configured
      </Badge>
    );
  }

  if (status.isValid === true) {
    return (
      <Badge variant="outline" className="gap-1.5 border-primary/20 bg-primary/10 text-primary">
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
  serviceType: 'embedding' | 'llm' | 'stt';
  description: string;
  onSaved: () => void;
}

export const ProviderSection = observer(function ProviderSection({
  serviceType,
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit selectedProvider to avoid infinite loop
  }, [resolvedDefault]);

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
  };

  const selectedStatus = providers.find((p) => p.provider === selectedProvider);

  if (providers.length === 0) return null;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{description}</p>

      {/* Provider selector with icon + status */}
      <div className="flex items-center gap-3">
        <Select value={selectedProvider} onValueChange={handleProviderChange}>
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="Select provider" />
          </SelectTrigger>
          <SelectContent>
            {providers.map((p) => (
              <SelectItem key={p.provider} value={p.provider}>
                <span className="flex items-center gap-2">
                  <ProviderIcon provider={p.provider} size={14} />
                  {PROVIDER_DISPLAY_NAMES[p.provider] ?? p.provider}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <StatusBadge status={selectedStatus} />
      </div>

      {/* Config form */}
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
    </div>
  );
});
