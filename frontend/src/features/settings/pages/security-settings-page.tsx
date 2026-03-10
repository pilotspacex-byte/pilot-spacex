/**
 * SecuritySettingsPage - Active sessions management and SCIM directory sync.
 *
 * AUTH-06: Admin UI for session visibility and termination.
 * AUTH-07: Admin UI for SCIM token generation.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { AlertCircle, Copy, Loader2, Monitor, Smartphone } from 'lucide-react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { useStore } from '@/stores';
import { ApiError } from '@/services/api';
import {
  useSessions,
  useTerminateSession,
  useTerminateAllUserSessions,
} from '../hooks/use-sessions';
import { useGenerateScimToken } from '../hooks/use-scim';

// ---- Helpers ----

function getInitials(name: string | null): string {
  if (!name) return '?';
  return name
    .split(' ')
    .map((n) => n[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const ts = new Date(isoString).getTime();
  const diffMs = now - ts;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function DeviceIcon({ device }: { device: string | null }) {
  if (device?.toLowerCase().includes('mobile')) {
    return <Smartphone className="h-4 w-4 text-muted-foreground" aria-hidden />;
  }
  return <Monitor className="h-4 w-4 text-muted-foreground" aria-hidden />;
}

// ---- Sub-components ----

function SessionsSkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <TableRow key={i}>
          <TableCell>
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-4 w-32" />
            </div>
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-24" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-28" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
          <TableCell />
        </TableRow>
      ))}
    </>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const handleCopy = () => {
    navigator.clipboard.writeText(value).catch(() => undefined);
    toast.success('Copied to clipboard');
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="h-7 w-7 p-0"
      onClick={handleCopy}
      aria-label={label}
    >
      <Copy className="h-3.5 w-3.5" />
    </Button>
  );
}

// ---- Main Component ----

export function SecuritySettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const isAdmin = workspaceStore.isAdmin;

  const {
    data: sessions,
    isLoading: sessionsLoading,
    error: sessionsError,
  } = useSessions(workspaceSlug);
  const terminateSession = useTerminateSession(workspaceSlug);
  const terminateAllUserSessions = useTerminateAllUserSessions(workspaceSlug);
  const generateScimToken = useGenerateScimToken(workspaceSlug);

  // Terminate single session dialog state
  const [terminateTarget, setTerminateTarget] = React.useState<{
    sessionId: string;
    displayName: string | null;
  } | null>(null);

  // Generate SCIM token dialog state
  const [showGenerateConfirm, setShowGenerateConfirm] = React.useState(false);
  const [generatedToken, setGeneratedToken] = React.useState<string | null>(null);

  const scimBaseUrl = `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/scim/v2/${workspaceSlug}`;

  const handleTerminateConfirm = async () => {
    if (!terminateTarget) return;
    try {
      await terminateSession.mutateAsync(terminateTarget.sessionId);
      toast.success('Session terminated');
    } catch (err) {
      const msg =
        err instanceof ApiError ? (err.detail ?? err.message) : 'Failed to terminate session';
      toast.error(msg);
    } finally {
      setTerminateTarget(null);
    }
  };

  const handleTerminateAllConfirm = async (userId: string, displayName: string | null) => {
    try {
      await terminateAllUserSessions.mutateAsync(userId);
      toast.success(`All sessions terminated for ${displayName ?? 'user'}`);
    } catch (err) {
      const msg =
        err instanceof ApiError ? (err.detail ?? err.message) : 'Failed to terminate sessions';
      toast.error(msg);
    }
  };

  const handleGenerateScimToken = async () => {
    setShowGenerateConfirm(false);
    try {
      const result = await generateScimToken.mutateAsync();
      setGeneratedToken(result.token);
    } catch (err) {
      const msg =
        err instanceof ApiError ? (err.detail ?? err.message) : 'Failed to generate SCIM token';
      toast.error(msg);
    }
  };

  // Admin-only guard
  if (!isAdmin) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Access restricted</AlertTitle>
          <AlertDescription>
            Only workspace admins and owners can manage security settings.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
          <p className="text-sm text-muted-foreground">
            Manage active sessions and directory sync configuration.
          </p>
        </div>

        {/* Active Sessions */}
        <Card>
          <CardHeader>
            <CardTitle>Active Sessions</CardTitle>
            <CardDescription>
              View and manage all authenticated sessions for this workspace.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sessionsError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Failed to load sessions</AlertTitle>
                <AlertDescription>
                  {sessionsError instanceof Error ? sessionsError.message : 'An error occurred.'}
                </AlertDescription>
              </Alert>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Member</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Device</TableHead>
                    <TableHead>Last Active</TableHead>
                    <TableHead className="w-[100px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessionsLoading ? (
                    <SessionsSkeletonRows />
                  ) : !sessions || sessions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                        No active sessions found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    sessions.map((session) => (
                      <TableRow key={session.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Avatar className="h-8 w-8">
                              <AvatarImage src={session.user_avatar_url ?? undefined} />
                              <AvatarFallback className="text-xs">
                                {getInitials(session.user_display_name)}
                              </AvatarFallback>
                            </Avatar>
                            <span className="font-medium">
                              {session.user_display_name ?? 'Unknown user'}
                            </span>
                            {session.is_current && (
                              <Badge variant="secondary" className="text-xs">
                                (you)
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-sm text-muted-foreground">
                          {session.ip_address ?? '—'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <DeviceIcon device={session.device} />
                            <span className="text-sm">
                              {[session.browser, session.os].filter(Boolean).join(' / ') || '—'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatRelativeTime(session.last_seen_at)}
                        </TableCell>
                        <TableCell>
                          {!session.is_current && (
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                                onClick={() =>
                                  setTerminateTarget({
                                    sessionId: session.id,
                                    displayName: session.user_display_name,
                                  })
                                }
                                aria-label={`Terminate session for ${session.user_display_name ?? 'user'}`}
                                disabled={terminateSession.isPending}
                              >
                                Terminate session
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-muted-foreground hover:text-destructive"
                                onClick={() =>
                                  handleTerminateAllConfirm(
                                    session.user_id,
                                    session.user_display_name
                                  )
                                }
                                aria-label={`Terminate all sessions for ${session.user_display_name ?? 'user'}`}
                                disabled={terminateAllUserSessions.isPending}
                              >
                                All
                              </Button>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Directory Sync (SCIM) */}
        <Card>
          <CardHeader>
            <CardTitle>Directory Sync</CardTitle>
            <CardDescription>
              Connect your identity provider to automatically provision and deprovision users.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* SCIM Base URL */}
            <div className="space-y-2">
              <Label htmlFor="scim-base-url">SCIM Base URL</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="scim-base-url"
                  type="text"
                  value={scimBaseUrl}
                  readOnly
                  className="font-mono text-sm sm:max-w-lg"
                  aria-label="SCIM Base URL"
                />
                <CopyButton value={scimBaseUrl} label="Copy SCIM Base URL" />
              </div>
              <p className="text-sm text-muted-foreground">
                Configure this as the SCIM endpoint in your identity provider.
              </p>
            </div>

            {/* SCIM Bearer Token */}
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium">Bearer Token</p>
                <p className="text-sm text-muted-foreground">
                  Generate a bearer token to use when configuring your IdP&apos;s SCIM client.
                </p>
              </div>
              <Alert className="border-amber-500/50 bg-amber-50 text-amber-900 dark:bg-amber-950/20 dark:text-amber-300">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Deprovisioned users&apos; data (issues, notes) is never deleted — only access is
                  revoked.
                </AlertDescription>
              </Alert>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowGenerateConfirm(true)}
                disabled={generateScimToken.isPending}
                aria-busy={generateScimToken.isPending}
              >
                {generateScimToken.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                )}
                Generate New SCIM Token
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Terminate Session AlertDialog */}
      <AlertDialog
        open={!!terminateTarget}
        onOpenChange={(open) => !open && setTerminateTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Terminate session</AlertDialogTitle>
            <AlertDialogDescription>
              Terminate session for <strong>{terminateTarget?.displayName ?? 'this user'}</strong>?
              They will be logged out immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleTerminateConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Terminate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Generate SCIM Token Confirmation AlertDialog */}
      <AlertDialog open={showGenerateConfirm} onOpenChange={setShowGenerateConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Generate new token?</AlertDialogTitle>
            <AlertDialogDescription>
              The previous SCIM token will be immediately invalidated. Any IdP configuration using
              the old token will stop working until you update it with the new token.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleGenerateScimToken}>Generate</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Generated Token Dialog (shown once) */}
      <Dialog open={!!generatedToken} onOpenChange={(open) => !open && setGeneratedToken(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>SCIM Token Generated</DialogTitle>
            <DialogDescription>
              Store this token securely. It will not be shown again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Token</Label>
              <div className="flex items-center gap-2">
                <code className="flex-1 break-all rounded bg-muted px-3 py-2 text-xs font-mono">
                  {generatedToken}
                </code>
                <CopyButton value={generatedToken ?? ''} label="Copy token" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Token generated. Configure your IdP&apos;s SCIM provisioner with the URL and token
              above.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
