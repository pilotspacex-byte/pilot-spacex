/**
 * MCPServerCard - Display a registered remote MCP server with status and actions.
 *
 * Phase 14 Plan 04: Shows server info, connection status badge, refresh status
 * button, and destructive delete action with AlertDialog confirmation.
 *
 * Plain component (NOT observer) — receives all data as props.
 */

'use client';

import { RefreshCw, Trash2, Server } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { McpStatusBadge } from './mcp-status-badge';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

interface MCPServerCardProps {
  server: MCPServer;
  onDelete: (serverId: string) => void;
  onRefreshStatus: (serverId: string) => void;
  onAuthorize?: (serverId: string) => void;
  isDeleting: boolean;
}

function AuthTypeBadge({ authType }: { authType: MCPServer['auth_type'] }) {
  const label = authType === 'bearer' ? 'Bearer' : authType === 'oauth2' ? 'OAuth2' : 'None';
  return (
    <Badge variant="outline" className="text-xs">
      {label}
    </Badge>
  );
}

export function MCPServerCard({
  server,
  onDelete,
  onRefreshStatus,
  onAuthorize,
  isDeleting,
}: MCPServerCardProps) {
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
              <p className="text-xs text-muted-foreground truncate">{server.url}</p>
              <div className="mt-1.5 flex items-center gap-2">
                <AuthTypeBadge authType={server.auth_type} />
                <McpStatusBadge status={server.last_status} />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex shrink-0 items-center gap-1">
            {server.auth_type === 'oauth2' && onAuthorize && (
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
