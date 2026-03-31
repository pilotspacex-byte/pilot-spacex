/**
 * ProfileCompletionForm — Collects full name after magic-link sign-in.
 *
 * S006: Shown after workspace invite acceptance when the user's full_name
 * is missing. Mirrors the onboarding profile step but is standalone.
 * On success, calls onComplete() so the parent can redirect.
 */

'use client';

import * as React from 'react';
import { Loader2, UserCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/services/api/client';
import { toast } from 'sonner';

interface ProfileCompletionFormProps {
  /** Called when profile is saved successfully. */
  onComplete: () => void;
}

interface UpdateMeRequest {
  full_name: string;
}

export function ProfileCompletionForm({ onComplete }: ProfileCompletionFormProps) {
  const [fullName, setFullName] = React.useState('');
  const [isPending, setIsPending] = React.useState(false);

  const isValid = fullName.trim().length >= 2;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setIsPending(true);
    try {
      await apiClient.patch<UpdateMeRequest>('/users/me', {
        full_name: fullName.trim(),
      });
      toast.success('Profile saved!');
      onComplete();
    } catch {
      toast.error('Failed to save profile. Please try again.');
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

      <Button
        type="submit"
        className="w-full"
        disabled={!isValid || isPending}
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
            Continue to workspace
          </>
        )}
      </Button>
    </form>
  );
}
