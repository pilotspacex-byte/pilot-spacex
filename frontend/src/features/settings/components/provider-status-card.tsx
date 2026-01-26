/**
 * ProviderStatusCard - Display AI provider connection status.
 *
 * T182: Show provider status (Anthropic, OpenAI), connection indicator, last validated.
 */

import { formatDistanceToNow } from 'date-fns';
import { CheckCircle2, XCircle, Circle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface ProviderStatus {
  provider: 'anthropic' | 'openai';
  is_key_set: boolean;
  last_validated_at?: string | null;
  status?: 'connected' | 'disconnected' | 'unknown';
}

export interface ProviderStatusCardProps {
  provider: 'anthropic' | 'openai';
  isKeySet: boolean;
  lastValidated?: string | null;
  status?: 'connected' | 'disconnected' | 'unknown';
}

const ProviderIcon = ({ provider }: { provider: 'anthropic' | 'openai' }) => {
  if (provider === 'anthropic') {
    return (
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10 text-orange-600">
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-600">
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" />
      </svg>
    </div>
  );
};

export function ProviderStatusCard({
  provider,
  isKeySet,
  lastValidated,
  status = 'unknown',
}: ProviderStatusCardProps) {
  const providerName = provider === 'anthropic' ? 'Anthropic' : 'OpenAI';

  const getStatusBadge = () => {
    if (!isKeySet) {
      return (
        <Badge variant="outline" className="gap-1.5">
          <Circle className="h-3 w-3 fill-muted-foreground text-muted-foreground" />
          Not configured
        </Badge>
      );
    }

    if (status === 'connected') {
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

    if (status === 'disconnected') {
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
  };

  const getLastValidatedText = () => {
    if (!lastValidated) {
      return isKeySet ? 'Not validated yet' : 'No API key set';
    }

    try {
      const distance = formatDistanceToNow(new Date(lastValidated), { addSuffix: true });
      return `Last validated ${distance}`;
    } catch {
      return 'Last validated recently';
    }
  };

  return (
    <Card className={cn('transition-colors', !isKeySet && 'opacity-75')}>
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <ProviderIcon provider={provider} />
          <div>
            <p className="font-medium">{providerName}</p>
            <p className="text-xs text-muted-foreground">{getLastValidatedText()}</p>
          </div>
        </div>
        {getStatusBadge()}
      </CardContent>
    </Card>
  );
}
