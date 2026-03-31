/**
 * SignupCompletionForm — Collects full name and password for new users arriving
 * via workspace invitation magic link.
 *
 * S012: Shown on /invite when a brand-new user needs to set their display name
 * and create a password. Password is set server-side via Supabase Admin API
 * by POST /auth/complete-signup, which also atomically updates the name and
 * accepts the invitation.
 */

'use client';

import * as React from 'react';
import { Loader2, UserCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/services/api/client';
import { toast } from 'sonner';

interface SignupCompletionFormProps {
  /** Workspace invitation ID to accept atomically with profile setup. */
  invitationId: string;
  /** Called with the workspace slug when signup is fully complete. */
  onComplete: (workspaceSlug: string) => void;
}

interface CompleteSignupResponse {
  workspace_slug: string;
}

export function SignupCompletionForm({ invitationId, onComplete }: SignupCompletionFormProps) {
  const [fullName, setFullName] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [isPending, setIsPending] = React.useState(false);

  const isNameValid = fullName.trim().length >= 2;
  const isPasswordValid = password.length >= 8;
  const isPasswordMatch = password === confirmPassword;
  const showPasswordMismatch = confirmPassword.length > 0 && !isPasswordMatch;
  const isFormValid = isNameValid && isPasswordValid && isPasswordMatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setIsPending(true);
    try {
      // Set password server-side and accept invitation in a single backend call
      const result = await apiClient.post<CompleteSignupResponse>('/auth/complete-signup', {
        invitation_id: invitationId,
        full_name: fullName.trim(),
        password,
      });

      toast.success('Welcome! Your account is ready.');
      onComplete(result.workspace_slug);
    } catch {
      toast.error('Failed to complete signup. Please try again.');
    } finally {
      setIsPending(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="full-name">Full name</Label>
        <Input
          id="full-name"
          type="text"
          placeholder="Your full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          autoComplete="name"
          autoFocus
          disabled={isPending}
          aria-required="true"
          aria-describedby="full-name-hint"
        />
        <p id="full-name-hint" className="text-xs text-muted-foreground">
          This is how your name appears to teammates.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          placeholder="Create a password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          disabled={isPending}
          aria-required="true"
          aria-describedby="password-hint"
        />
        <p id="password-hint" className="text-xs text-muted-foreground">
          Minimum 8 characters.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirm-password">Confirm password</Label>
        <Input
          id="confirm-password"
          type="password"
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
          disabled={isPending}
          aria-required="true"
          aria-invalid={showPasswordMismatch}
          aria-describedby={showPasswordMismatch ? 'password-mismatch' : undefined}
        />
        {showPasswordMismatch && (
          <p id="password-mismatch" className="text-xs text-destructive" role="alert">
            Passwords do not match.
          </p>
        )}
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={!isFormValid || isPending}
        aria-busy={isPending}
      >
        {isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            Saving…
          </>
        ) : (
          <>
            <UserCheck className="mr-2 h-4 w-4" aria-hidden="true" />
            Complete account
          </>
        )}
      </Button>
    </form>
  );
}
