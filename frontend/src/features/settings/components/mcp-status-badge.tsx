/**
 * McpStatusBadge - 5-state visual status indicator for MCP servers.
 *
 * Pure component, no store dependency. Maps McpStatus to colour + label + icon.
 */

import { AlertTriangle, CircleX } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { McpStatus } from '@/stores/ai/MCPServersStore';

interface McpStatusBadgeProps {
  status: McpStatus | null;
}

const STATUS_CONFIG: Record<
  McpStatus,
  { label: string; dotColor: string; className: string; icon?: 'alert' | 'circle-x' }
> = {
  enabled: {
    label: 'Enabled',
    dotColor: 'bg-green-500',
    className: 'border-green-500/20 bg-green-500/10 text-green-700 dark:text-green-400',
  },
  disabled: {
    label: 'Disabled',
    dotColor: 'bg-gray-400',
    className: 'border-gray-400/20 bg-gray-400/10 text-gray-600 dark:text-gray-400',
  },
  unhealthy: {
    label: 'Unhealthy',
    dotColor: 'bg-amber-500',
    className: 'border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-400',
    icon: 'alert',
  },
  unreachable: {
    label: 'Unreachable',
    dotColor: 'bg-red-500',
    className: 'border-red-500/20 bg-red-500/10 text-red-700 dark:text-red-400',
    icon: 'circle-x',
  },
  config_error: {
    label: 'Config Error',
    dotColor: 'bg-red-500',
    className: 'border-red-500/20 bg-red-500/10 text-red-700 dark:text-red-400',
    icon: 'alert',
  },
};

export function McpStatusBadge({ status }: McpStatusBadgeProps) {
  if (!status) {
    return (
      <Badge variant="secondary" className="gap-1.5 text-xs">
        <span className="h-2 w-2 rounded-full bg-gray-400" />
        Unknown
      </Badge>
    );
  }

  const config = STATUS_CONFIG[status];

  return (
    <Badge variant="outline" className={`gap-1.5 text-xs ${config.className}`}>
      {config.icon === 'alert' ? (
        <AlertTriangle className="h-3 w-3" />
      ) : config.icon === 'circle-x' ? (
        <CircleX className="h-3 w-3" />
      ) : (
        <span className={`h-2 w-2 rounded-full ${config.dotColor}`} />
      )}
      {config.label}
    </Badge>
  );
}
