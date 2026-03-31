'use client';

/**
 * Invite page — two-step magic link registration flow.
 *
 * US1: New user flow
 *   1. Reads invitation_id from URL params
 *   2. Previews invitation (workspace name, status) via public GET /invitations/{id}/preview
 *   3. If PENDING: shows email form ("Join [workspace_name]")
 *   4. On submit: calls POST /invitations/{id}/request-magic-link → shows success state
 *
 * US2: Existing user fast path
 *   - Detects existing Supabase session on mount
 *   - If SIGNED_IN: skips email form, shows SignupCompletionForm directly
 *
 * Source: FR-012, FR-013, spec.md US1, US2
 */

import {
  previewInvitation,
  requestMagicLink,
  type InvitationPreviewResponse,
} from '@/features/members/hooks/use-workspace-invitations';
import { SignupCompletionForm } from '@/features/auth/components/signup-completion-form';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import * as React from 'react';

type PageState =
  | 'loading'
  | 'form'
  | 'submitting'
  | 'success'
  | 'complete_profile'
  | 'error_expired'
  | 'error_revoked'
  | 'error_accepted'
  | 'error_generic';

export default function InvitePage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const invitationId = searchParams.get('invitation_id');

  const [pageState, setPageState] = React.useState<PageState>('loading');
  const [preview, setPreview] = React.useState<InvitationPreviewResponse | null>(null);
  const [email, setEmail] = React.useState('');
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const handleError = React.useCallback((state: PageState, msg?: string) => {
    setErrorMessage(msg ?? null);
    setPageState(state);
  }, []);

  // US2: Check for existing session on mount — fast path for already-logged-in users
  React.useEffect(() => {
    if (!invitationId) {
      handleError('error_generic', 'Missing invitation ID. Please use the link from your invitation email.');
      return;
    }

    let settled = false;

    const settle = (hasSession: boolean) => {
      if (settled) return;
      settled = true;
      subscription.unsubscribe();
      clearTimeout(debounceTimer);

      if (hasSession) {
        // US2 fast path: existing session — show completion form directly
        setPageState('complete_profile');
      } else {
        // US1 path: no session — load preview then show email form
        previewInvitation(invitationId)
          .then((data) => {
            setPreview(data);
            setPageState('form');
          })
          .catch((err: unknown) => {
            const status = (err as { status?: number })?.status;
            if (status === 404) {
              handleError('error_generic', 'Invitation not found.');
            } else if (status === 410) {
              const invStatus = (err as { data?: { details?: { invitation_status?: string } } })
                ?.data?.details?.invitation_status;
              if (invStatus === 'revoked' || invStatus === 'cancelled') {
                handleError('error_revoked');
              } else if (invStatus === 'accepted') {
                handleError('error_accepted');
              } else {
                handleError('error_expired');
              }
            } else {
              handleError('error_generic', 'Unable to load invitation details.');
            }
          });
      }
    };

    // 500ms debounce: if no session event within 500ms, treat as no session
    const debounceTimer = setTimeout(() => settle(false), 500);

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        settle(true);
      }
    });

    // Fast path: session already present
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        settle(true);
      }
    });

    return () => {
      subscription.unsubscribe();
      clearTimeout(debounceTimer);
    };
  }, [invitationId, router, handleError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invitationId || !email.trim()) return;

    setPageState('submitting');

    try {
      await requestMagicLink(invitationId, email.trim());
      setPageState('success');
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 429) {
        handleError(
          'error_generic',
          'Too many magic link requests. Please wait before trying again.',
        );
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to send magic link.';
        handleError('error_generic', msg);
      }
    }
  };

  // ── Complete profile (user needs name + password) ────────────────────────
  if (pageState === 'complete_profile' && invitationId) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">Complete your account</h1>
            <p className="text-sm text-muted-foreground">
              Set your name and password to finish joining your workspace.
            </p>
          </div>
          <SignupCompletionForm
            invitationId={invitationId}
            onComplete={(slug) => router.push(`/${slug}`)}
          />
        </div>
      </div>
    );
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (pageState === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading invitation…</p>
        </div>
      </div>
    );
  }

  // ── Error states ─────────────────────────────────────────────────────────
  if (
    pageState === 'error_expired' ||
    pageState === 'error_revoked' ||
    pageState === 'error_accepted' ||
    pageState === 'error_generic'
  ) {
    const errorContent = {
      error_expired: {
        title: 'Invitation expired',
        body: 'This invitation link has expired. Please contact your workspace admin to send a new invitation.',
      },
      error_revoked: {
        title: 'Invitation revoked',
        body: 'This invitation has been revoked by a workspace admin. Please contact them if you believe this is a mistake.',
      },
      error_accepted: {
        title: 'Invitation already used',
        body: 'This invitation has already been accepted. If you need access, please contact your workspace admin.',
      },
      error_generic: {
        title: 'Something went wrong',
        body: errorMessage ?? 'An unexpected error occurred. Please try again.',
      },
    }[pageState];

    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center space-y-2 max-w-sm">
          <h1 className="text-lg font-semibold text-destructive">{errorContent.title}</h1>
          <p className="text-sm text-muted-foreground">{errorContent.body}</p>
        </div>
      </div>
    );
  }

  // ── Success state ────────────────────────────────────────────────────────
  if (pageState === 'success') {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md space-y-4 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Check your email</h1>
          <p className="text-sm text-muted-foreground">
            We&apos;ve sent a magic link to <strong>{email}</strong>. Click the link in the
            email to join{' '}
            {preview?.workspace_name ? (
              <strong>{preview.workspace_name}</strong>
            ) : (
              'the workspace'
            )}
            .
          </p>
          <p className="text-xs text-muted-foreground">The link expires in 60 minutes.</p>
        </div>
      </div>
    );
  }

  // ── Email form (US1 main state) ──────────────────────────────────────────
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            Join{preview?.workspace_name ? ` ${preview.workspace_name}` : ' workspace'}
          </h1>
          <p className="text-sm text-muted-foreground">
            You&apos;ve been invited{preview?.workspace_name ? ` to ${preview.workspace_name}` : ''}
            . Enter your email to receive a magic link and create your account.
          </p>
          {preview?.invited_email_masked && (
            <p className="text-xs text-muted-foreground">
              Invitation sent to{' '}
              <span className="font-mono">{preview.invited_email_masked}</span>
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              disabled={pageState === 'submitting'}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={pageState === 'submitting' || !email.trim()}
          >
            {pageState === 'submitting' ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending magic link…
              </>
            ) : (
              'Send Magic Link'
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
