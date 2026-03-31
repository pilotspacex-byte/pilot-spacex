/**
 * AccessDenied — Shown when a user attempts to access a project they are not
 * assigned to (HTTP 403 / project_access_denied).
 *
 * T039 [US6]: WCAG AA compliant; provides workspace navigation link.
 */

'use client';

import { Button } from '@/components/ui/button';
import { Lock } from 'lucide-react';
import Link from 'next/link';

interface AccessDeniedProps {
  /** Custom message shown beneath the heading. */
  message?: string;
  /** Href for the "Go back" button. Defaults to the workspace root. */
  backHref?: string;
  /** Label for the back button. */
  backLabel?: string;
}

export function AccessDenied({
  message = "You don't have access to this project. Ask a workspace admin to add you.",
  backHref = '/',
  backLabel = 'Back to workspace',
}: AccessDeniedProps) {
  return (
    <div
      role="main"
      aria-labelledby="access-denied-heading"
      className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Lock className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
      </div>

      <div className="space-y-2 max-w-sm">
        <h1
          id="access-denied-heading"
          className="text-xl font-semibold tracking-tight text-foreground"
        >
          Access Denied
        </h1>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>

      <Button asChild variant="outline">
        <Link href={backHref}>{backLabel}</Link>
      </Button>
    </div>
  );
}
