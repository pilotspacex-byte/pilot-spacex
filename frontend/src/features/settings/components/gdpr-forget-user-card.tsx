/**
 * GdprForgetUserCard — danger-zone admin action to hard-delete all memories
 * for a given user_id (GDPR Right to Erasure).
 *
 * Phase 69 long-term memory.
 */

'use client';

import * as React from 'react';
import { AlertTriangle } from 'lucide-react';
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
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useGdprForgetUser } from '../hooks/use-ai-memory';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface GdprForgetUserCardProps {
  workspaceId: string | undefined;
}

export function GdprForgetUserCard({ workspaceId }: GdprForgetUserCardProps) {
  const [userId, setUserId] = React.useState('');
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const forget = useGdprForgetUser(workspaceId);

  const isValid = UUID_RE.test(userId.trim());

  const handleConfirm = () => {
    forget.mutate(userId.trim(), {
      onSettled: () => {
        setConfirmOpen(false);
        setUserId('');
      },
    });
  };

  return (
    <Card className="border-destructive/40">
      <CardHeader className="pb-4">
        <CardTitle className="text-base flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          GDPR — Forget User Memories
        </CardTitle>
        <CardDescription>
          Permanently delete all AI memories associated with a specific user. This is irreversible
          and intended for compliance with the Right to Erasure (GDPR Art. 17).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="gdpr-user-id">User ID (UUID)</Label>
          <Input
            id="gdpr-user-id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
            aria-invalid={userId.length > 0 && !isValid}
            aria-describedby={userId.length > 0 && !isValid ? 'gdpr-error' : undefined}
            className="font-mono text-xs"
          />
          {userId.length > 0 && !isValid && (
            <p id="gdpr-error" className="text-xs text-destructive" role="alert">Must be a valid UUID.</p>
          )}
        </div>
        <Button
          type="button"
          variant="destructive"
          size="sm"
          disabled={!isValid || forget.isPending}
          onClick={() => setConfirmOpen(true)}
        >
          {forget.isPending ? 'Erasing…' : 'Delete all memories for this user'}
        </Button>

        <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Permanently erase user memories?</AlertDialogTitle>
              <AlertDialogDescription>
                This will hard-delete every AI memory linked to user{' '}
                <code className="text-xs">{userId}</code>. The action is irreversible and
                compliance-gated. A record of this deletion is written to the audit log.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleConfirm}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Yes, erase permanently
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  );
}
