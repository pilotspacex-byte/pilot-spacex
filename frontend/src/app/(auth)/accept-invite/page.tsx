'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Users, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/lib/supabase';
import { ApiError, apiClient } from '@/services/api';

interface InvitationDetails {
  id: string;
  workspaceName: string;
  workspaceSlug: string;
  inviterName: string | null;
  role: string;
  emailMasked: string;
  status: string;
  expiresAt: string;
}

type PageState =
  | { kind: 'loading' }
  | { kind: 'details'; invitation: InvitationDetails }
  | { kind: 'accepting' }
  | { kind: 'accepted'; workspaceSlug: string; workspaceName: string }
  | { kind: 'error'; message: string }
  | { kind: 'expired' }
  | { kind: 'unauthenticated'; invitation: InvitationDetails };

/**
 * Accept-invite page — handles invitation acceptance flow.
 *
 * Flows:
 * 1. Supabase magic link → tokens in URL hash → auto-accept → redirect to workspace
 * 2. Already authenticated → show accept button → accept → redirect
 * 3. Not authenticated → show login/signup CTA with invitation context
 */
export default function AcceptInvitePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invitationId = searchParams.get('invitation_id');
  const [state, setState] = useState<PageState>({ kind: 'loading' });

  useEffect(() => {
    if (!invitationId) {
      setState({ kind: 'error', message: 'No invitation ID provided.' });
      return;
    }

    handleInvitation(invitationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invitationId]);

  async function handleInvitation(id: string) {
    // 1. Fetch invitation details (public, no auth)
    let invitation: InvitationDetails;
    try {
      invitation = await apiClient.get<InvitationDetails>(`/invitations/${id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setState({ kind: 'error', message: 'Invitation not found or has expired.' });
      } else {
        setState({ kind: 'error', message: 'Unable to load invitation. Please try again.' });
      }
      return;
    }

    if (invitation.status !== 'pending') {
      if (invitation.status === 'expired') {
        setState({ kind: 'expired' });
      } else {
        setState({ kind: 'error', message: `This invitation has already been ${invitation.status}.` });
      }
      return;
    }

    // 2. Check for Supabase tokens in URL hash (from magic link email)
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const accessToken = hashParams.get('access_token');
    const refreshToken = hashParams.get('refresh_token');

    if (accessToken && refreshToken) {
      // Magic link flow — set session and auto-accept
      setState({ kind: 'accepting' });
      // Clear tokens from URL hash immediately to prevent leakage via history/sharing
      window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
      try {
        await supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken });
        const result = await apiClient.post<{ workspaceSlug: string; workspaceName: string }>(
          `/invitations/${id}/accept`
        );
        setState({ kind: 'accepted', workspaceSlug: result.workspaceSlug, workspaceName: result.workspaceName });
        setTimeout(() => router.push(`/${result.workspaceSlug}`), 1500);
      } catch {
        setState({ kind: 'error', message: 'Failed to accept invitation. Please try logging in.' });
      }
      return;
    }

    // 3. Check if user is already authenticated
    const { data: sessionData } = await supabase.auth.getSession();
    if (sessionData.session) {
      setState({ kind: 'details', invitation });
      return;
    }

    // 4. Not authenticated — show CTA
    setState({ kind: 'unauthenticated', invitation });
  }

  async function handleAccept() {
    if (!invitationId) return;
    setState({ kind: 'accepting' });
    try {
      const result = await apiClient.post<{ workspaceSlug: string; workspaceName: string }>(
        `/invitations/${invitationId}/accept`
      );
      setState({ kind: 'accepted', workspaceSlug: result.workspaceSlug, workspaceName: result.workspaceName });
      setTimeout(() => router.push(`/${result.workspaceSlug}`), 1500);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to accept invitation.';
      setState({ kind: 'error', message });
    }
  }

  function handleLoginRedirect() {
    const redirect = `/accept-invite?invitation_id=${invitationId}`;
    router.push(`/login?redirect=${encodeURIComponent(redirect)}`);
  }

  // === Render ===

  if (state.kind === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading invitation...</p>
      </div>
    );
  }

  if (state.kind === 'accepting') {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Joining workspace...</p>
      </div>
    );
  }

  if (state.kind === 'accepted') {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 text-center">
        <CheckCircle2 className="h-12 w-12 text-green-500" />
        <h2 className="text-lg font-semibold">Welcome!</h2>
        <p className="text-sm text-muted-foreground">
          You&apos;ve joined <strong>{state.workspaceName}</strong>. Redirecting...
        </p>
      </div>
    );
  }

  if (state.kind === 'expired') {
    return (
      <Card>
        <CardHeader className="text-center">
          <XCircle className="mx-auto h-12 w-12 text-muted-foreground" />
          <CardTitle className="mt-4">Invitation Expired</CardTitle>
          <CardDescription>
            This invitation has expired. Please ask the workspace admin to send a new one.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button variant="outline" onClick={() => router.push('/login')}>
            Go to Login
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (state.kind === 'error') {
    return (
      <Card>
        <CardHeader className="text-center">
          <XCircle className="mx-auto h-12 w-12 text-destructive" />
          <CardTitle className="mt-4">Something went wrong</CardTitle>
          <CardDescription>{state.message}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button variant="outline" onClick={() => router.push('/login')}>
            Go to Login
          </Button>
        </CardContent>
      </Card>
    );
  }

  const invitation = state.invitation;

  return (
    <Card>
      <CardHeader className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <Users className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="mt-4">You&apos;re invited!</CardTitle>
        <CardDescription>
          {invitation.inviterName ? (
            <>
              <strong>{invitation.inviterName}</strong> has invited you to join
            </>
          ) : (
            <>You&apos;ve been invited to join</>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Workspace</span>
            <span className="font-medium">{invitation.workspaceName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Role</span>
            <Badge variant="secondary" className="capitalize">
              {invitation.role}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Invited as</span>
            <span className="text-sm">{invitation.emailMasked}</span>
          </div>
        </div>

        {state.kind === 'details' ? (
          <Button className="w-full" size="lg" onClick={handleAccept}>
            Join Workspace
          </Button>
        ) : (
          <div className="space-y-3">
            <Button className="w-full" size="lg" onClick={handleLoginRedirect}>
              Sign up or Log in to Join
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              Create an account or log in with the invited email to accept
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
