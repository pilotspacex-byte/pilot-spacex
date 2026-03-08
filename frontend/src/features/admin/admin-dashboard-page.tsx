'use client';

/**
 * AdminDashboardPage — Super-admin operator dashboard.
 *
 * TENANT-04: Standalone read-only dashboard for self-hosted operators.
 * Intentionally outside the (workspace) route group — no workspace nav shell,
 * no MobX workspace store. Plain React component with TanStack Query.
 *
 * Auth gate: token is stored in sessionStorage (cleared on tab close).
 * Submit form → setItem('admin_token', token) → query enabled.
 * Sign Out → removeItem('admin_token') → returns to token form.
 */

import * as React from 'react';
import { AlertCircle, ChevronDown, ChevronRight, Loader2, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAdminWorkspaces, type AdminWorkspace } from './hooks/use-admin-workspaces';
import { WorkspaceDetailExpanded } from './workspace-detail-expanded';

// ---- Helpers ----

function formatRelativeDate(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = Date.now();
    const diffMs = now - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  } catch {
    return isoString;
  }
}

function formatStorageMb(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ---- Token form ----

interface TokenFormProps {
  onTokenSubmit: (token: string) => void;
}

function TokenForm({ onTokenSubmit }: TokenFormProps) {
  const [tokenInput, setTokenInput] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = tokenInput.trim();
    if (!trimmed) return;
    onTokenSubmit(trimmed);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Operator Dashboard</CardTitle>
          <CardDescription>
            Enter your super-admin token to access the workspace health dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="admin-token">Admin Token</Label>
              <Input
                id="admin-token"
                type="password"
                placeholder="Paste PILOT_SPACE_SUPER_ADMIN_TOKEN"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                autoComplete="off"
              />
            </div>
            <Button type="submit" className="w-full" disabled={!tokenInput.trim()}>
              Access Dashboard
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Workspace table row ----

interface WorkspaceRowProps {
  workspace: AdminWorkspace;
  token: string;
  isExpanded: boolean;
  onToggle: () => void;
}

function WorkspaceRow({ workspace: ws, token, isExpanded, onToggle }: WorkspaceRowProps) {
  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <TableCell>
          <div className="flex items-center gap-1">
            {isExpanded ? (
              <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
            )}
            <span className="font-medium">{ws.name}</span>
            <span className="text-xs text-muted-foreground">/{ws.slug}</span>
          </div>
        </TableCell>
        <TableCell className="text-center">{ws.member_count}</TableCell>
        <TableCell>{ws.owner_email ?? '—'}</TableCell>
        <TableCell>{ws.last_active ? formatRelativeDate(ws.last_active) : 'Never'}</TableCell>
        <TableCell>{formatStorageMb(ws.storage_used_bytes)}</TableCell>
        <TableCell className="text-center">{ws.ai_action_count}</TableCell>
        <TableCell className="text-center">
          {ws.rate_limit_violation_count > 0 ? (
            <span className="font-medium text-destructive">{ws.rate_limit_violation_count}</span>
          ) : (
            <span className="text-muted-foreground">0</span>
          )}
        </TableCell>
      </TableRow>

      {isExpanded && (
        <TableRow>
          <TableCell colSpan={7} className="bg-muted/20 px-6">
            <WorkspaceDetailExpanded token={token} slug={ws.slug} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ---- Skeleton rows for loading state ----

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: 7 }).map((__, j) => (
            <TableCell key={j}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

// ---- Main page ----

export function AdminDashboardPage() {
  const [token, setToken] = React.useState<string>(() => {
    if (typeof window === 'undefined') return '';
    return sessionStorage.getItem('admin_token') ?? '';
  });

  const [expandedSlug, setExpandedSlug] = React.useState<string | null>(null);

  const { data: workspaces, isLoading, error, refetch, isFetching } = useAdminWorkspaces(token);

  const handleTokenSubmit = (submittedToken: string) => {
    sessionStorage.setItem('admin_token', submittedToken);
    setToken(submittedToken);
  };

  const handleLogout = () => {
    sessionStorage.removeItem('admin_token');
    setToken('');
    setExpandedSlug(null);
  };

  const handleToggleRow = (slug: string) => {
    setExpandedSlug((prev) => (prev === slug ? null : slug));
  };

  const handleRefresh = () => {
    void refetch();
  };

  // --- Token form gate ---
  if (!token) {
    return <TokenForm onTokenSubmit={handleTokenSubmit} />;
  }

  // --- Dashboard ---
  const isInvalidToken = error instanceof Error && error.message.toLowerCase().includes('invalid');

  return (
    <div className="container mx-auto py-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Operator Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Read-only view of all workspace health metrics
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
              {isFetching ? (
                <Loader2 className="mr-2 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-3 w-3" />
              )}
              Refresh
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              Sign Out
            </Button>
          </div>
        </div>

        {/* Invalid token error */}
        {isInvalidToken && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Invalid token</AlertTitle>
            <AlertDescription>
              The admin token was rejected. Sign out and enter the correct token.
            </AlertDescription>
          </Alert>
        )}

        {/* Generic fetch error (not auth) */}
        {error && !isInvalidToken && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Failed to load workspaces</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </AlertDescription>
          </Alert>
        )}

        {/* Workspace table */}
        <Card>
          <CardHeader>
            <CardTitle>
              Workspaces
              {workspaces != null && (
                <span className="ml-2 text-base font-normal text-muted-foreground">
                  ({workspaces.length})
                </span>
              )}
            </CardTitle>
            <CardDescription>
              Click a row to expand top members, recent AI actions, and quota configuration.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Workspace</TableHead>
                  <TableHead className="text-center">Members</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Last Active</TableHead>
                  <TableHead>Storage</TableHead>
                  <TableHead className="text-center">AI Actions</TableHead>
                  <TableHead className="text-center">Rate Violations</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && <SkeletonRows />}

                {!isLoading && !error && workspaces?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      No workspaces found.
                    </TableCell>
                  </TableRow>
                )}

                {!isLoading &&
                  workspaces?.map((ws) => (
                    <WorkspaceRow
                      key={ws.id}
                      workspace={ws}
                      token={token}
                      isExpanded={expandedSlug === ws.slug}
                      onToggle={() => handleToggleRow(ws.slug)}
                    />
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
