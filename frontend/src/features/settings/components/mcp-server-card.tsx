/**
 * MCPServerCard - Display a registered remote MCP server with status and actions.
 *
 * Phase 14 Plan 04: Shows server info, connection status badge, refresh status
 * button, and destructive delete action with AlertDialog confirmation.
 *
 * Plain component (NOT observer) — receives all data as props.
 */

'use client';

import {
  RefreshCw,
  Trash2,
  CheckCircle2,
  XCircle,
  Circle,
  Server,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

interface MCPServerCardProps {
  server: MCPServer;
  onDelete: (serverId: string) => void;
  onRefreshStatus: (serverId: string) => void;
  onAuthorize?: (serverId: string) => void;
  onUpdateApprovalMode?: (serverId: string, mode: 'auto_approve' | 'require_approval') => void;
  isDeleting: boolean;
}

function StatusBadge({ status }: { status: MCPServer['last_status'] }) {
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

  if (status === 'failed') {
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
      Unknown
    </Badge>
  );
}

function AuthTypeBadge({ authType }: { authType: MCPServer['auth_type'] }) {
  return (
    <Badge variant="outline" className="text-xs">
      {authType === 'bearer' ? 'Bearer' : 'OAuth2'}
    </Badge>
  );
}

function StdioTransportBadge() {
  return (
    <Badge
      variant="outline"
      className="text-xs border-violet-500/20 bg-violet-500/10 text-violet-600"
    >
      Stdio
    </Badge>
  );
}

function ExpiryBadge({ expiresAt }: { expiresAt: string | null }) {
  if (!expiresAt) return null;
  const expiry = new Date(expiresAt);
  const now = new Date();
  const diffMs = expiry.getTime() - now.getTime();
  if (diffMs <= 0) {
    return (
      <Badge
        variant="outline"
        className="gap-1.5 border-destructive/20 bg-destructive/10 text-destructive text-xs"
      >
        <AlertCircle className="h-3 w-3" />
        Token expired
      </Badge>
    );
  }
  const diffH = Math.floor(diffMs / 3600000);
  const label = diffH < 1 ? 'expires in <1h' : `expires in ${diffH}h`;
  return (
    <Badge variant="outline" className="gap-1.5 text-xs text-muted-foreground">
      <Clock className="h-3 w-3" />
      {label}
    </Badge>
  );
}

export function MCPServerCard({
  server,
  onDelete,
  onRefreshStatus,
  onAuthorize,
  onUpdateApprovalMode,
  isDeleting,
}: MCPServerCardProps) {
  const isRequireApproval = server.approval_mode === 'require_approval';

  const handleApprovalModeChange = (checked: boolean) => {
    if (onUpdateApprovalMode) {
      onUpdateApprovalMode(server.id, checked ? 'require_approval' : 'auto_approve');
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Server info */}
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <Server className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="font-medium truncate">{server.display_name}</p>
              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                {server.transport_type === 'stdio'
                  ? `${server.stdio_command ?? ''} ${server.stdio_args ? (JSON.parse(server.stdio_args) as string[]).join(' ') : ''}`.trim()
                  : (server.url ?? '')}
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                {server.transport_type === 'stdio' ? (
                  <StdioTransportBadge />
                ) : (
                  <AuthTypeBadge authType={server.auth_type} />
                )}
                <StatusBadge status={server.last_status} />
                {server.auth_type === 'oauth2' && server.transport_type !== 'stdio' && (
                  <ExpiryBadge expiresAt={server.token_expires_at} />
                )}
              </div>
              {/* Approval mode toggle */}
              <div className="mt-2 flex items-center gap-2">
                <Switch
                  id={`approval-mode-${server.id}`}
                  size="sm"
                  checked={isRequireApproval}
                  onCheckedChange={handleApprovalModeChange}
                  aria-label="Require approval for tool calls"
                />
                <label
                  htmlFor={`approval-mode-${server.id}`}
                  className="cursor-pointer select-none text-xs text-muted-foreground"
                >
                  Require approval for tool calls
                </label>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex shrink-0 items-center gap-1">
            {server.transport_type !== 'stdio' && server.auth_type === 'oauth2' && onAuthorize && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => onAuthorize(server.id)}
                title="Authorize OAuth2 connection"
              >
                Authorize
              </Button>
            )}

            {server.transport_type !== 'stdio' && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => onRefreshStatus(server.id)}
                title="Refresh status"
                aria-label={`Refresh status for ${server.display_name}`}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  disabled={isDeleting}
                  aria-label={`Delete ${server.display_name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Remove MCP Server</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to remove <strong>{server.display_name}</strong>? This
                    action cannot be undone. The server will no longer be available to the AI agent.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onDelete(server.id)}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Remove
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
