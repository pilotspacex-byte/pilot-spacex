/**
 * EncryptionSettingsPage - Workspace bring-your-own-key encryption configuration.
 *
 * TENANT-02: Owner-only key upload, rotate, verify, and generate.
 * Non-owner members see read-only status.
 *
 * Plain React (NO observer()) — TanStack Query for all data.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { Eye, EyeOff, KeyRound, Loader2, ShieldCheck, ShieldOff } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';
import { ApiError } from '@/services/api';
import {
  useEncryptionStatus,
  useUploadEncryptionKey,
  useVerifyEncryptionKey,
  useGenerateEncryptionKey,
} from '../hooks/use-workspace-encryption';

// ---- Helpers ----

function formatDate(isoString: string | null): string {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.detail ?? err.message;
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred.';
}

// ---- Sub-components ----

function StatusSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-6 w-24" />
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-4 w-40" />
    </div>
  );
}

function EncryptionStatusDisplay({
  enabled,
  keyHint,
  keyVersion,
  lastRotated,
}: {
  enabled: boolean;
  keyHint: string | null;
  keyVersion: number | null;
  lastRotated: string | null;
}) {
  if (!enabled) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldOff className="h-4 w-4 text-muted-foreground" aria-hidden />
          <Badge variant="secondary">Disabled</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          No encryption key configured. Data is stored in plaintext.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-green-600 dark:text-green-400" aria-hidden />
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
          Enabled
        </Badge>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Key hint</dt>
        <dd className="font-mono">...{keyHint ?? '—'}</dd>
        <dt className="text-muted-foreground">Key version</dt>
        <dd>{keyVersion ?? '—'}</dd>
        <dt className="text-muted-foreground">Last rotated</dt>
        <dd>{formatDate(lastRotated)}</dd>
      </dl>
    </div>
  );
}

// ---- Main Component ----

export const EncryptionSettingsPage = observer(function EncryptionSettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const isOwner = workspaceStore.isOwner;

  // Query
  const { data: status, isLoading, error: statusError } = useEncryptionStatus(workspaceSlug);

  // Mutations
  const uploadKey = useUploadEncryptionKey(workspaceSlug);
  const verifyKey = useVerifyEncryptionKey(workspaceSlug);
  const generateKey = useGenerateEncryptionKey(workspaceSlug);

  // Local state
  const [keyInput, setKeyInput] = React.useState('');
  const [showKey, setShowKey] = React.useState(false);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [verifyResult, setVerifyResult] = React.useState<'success' | 'failed' | null>(null);

  const handleGenerateKey = async () => {
    try {
      const result = await generateKey.mutateAsync();
      setKeyInput(result.key);
      setShowKey(true);
      setVerifyResult(null);
      setUploadError(null);
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  const handleUploadKey = async () => {
    if (!keyInput.trim()) {
      setUploadError('Key is required.');
      return;
    }
    setUploadError(null);
    setVerifyResult(null);
    try {
      await uploadKey.mutateAsync(keyInput.trim());
      toast.success('Encryption key configured');
      setKeyInput('');
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    }
  };

  const handleVerifyKey = async () => {
    if (!keyInput.trim()) {
      setUploadError('Enter a key to verify.');
      return;
    }
    setUploadError(null);
    setVerifyResult(null);
    try {
      const result = await verifyKey.mutateAsync(keyInput.trim());
      setVerifyResult(result.verified ? 'success' : 'failed');
    } catch (err) {
      setVerifyResult('failed');
      setUploadError(extractErrorMessage(err));
    }
  };

  const uploadLabel = status?.enabled ? 'Rotate Key' : 'Enable Encryption';
  const anyMutationPending = uploadKey.isPending || verifyKey.isPending || generateKey.isPending;

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Workspace Encryption</h1>
          <p className="text-sm text-muted-foreground">
            Configure bring-your-own-key encryption for sensitive workspace data. Notes, issue
            descriptions, and AI inputs/outputs are encrypted with your key.
          </p>
        </div>

        {/* Status Card */}
        <Card>
          <CardHeader>
            <CardTitle>Encryption Status</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <StatusSkeleton />
            ) : statusError ? (
              <Alert variant="destructive">
                <AlertTitle>Failed to load encryption status</AlertTitle>
                <AlertDescription>{extractErrorMessage(statusError)}</AlertDescription>
              </Alert>
            ) : status ? (
              <EncryptionStatusDisplay
                enabled={status.enabled}
                keyHint={status.key_hint}
                keyVersion={status.key_version}
                lastRotated={status.last_rotated}
              />
            ) : null}
          </CardContent>
        </Card>

        {/* Configure Key Card — owner only */}
        {isOwner && (
          <Card>
            <CardHeader>
              <CardTitle>Configure Encryption Key</CardTitle>
              <CardDescription>
                Provide a 32-byte URL-safe base64 key. Use the Generate button to create one.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Key input with show/hide toggle */}
              <div className="space-y-2">
                <Label htmlFor="encryption-key">Encryption Key</Label>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="encryption-key"
                      type={showKey ? 'text' : 'password'}
                      value={keyInput}
                      onChange={(e) => {
                        setKeyInput(e.target.value);
                        setUploadError(null);
                        setVerifyResult(null);
                      }}
                      placeholder="Enter or generate a 32-byte base64 key"
                      className="pr-10 font-mono text-sm"
                      aria-label="Encryption key"
                      aria-invalid={!!uploadError}
                      aria-describedby={uploadError ? 'key-error' : undefined}
                      disabled={anyMutationPending}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0"
                      onClick={() => setShowKey((v) => !v)}
                      aria-label={showKey ? 'Hide key' : 'Show key'}
                      tabIndex={-1}
                    >
                      {showKey ? (
                        <EyeOff className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                      ) : (
                        <Eye className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                      )}
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleGenerateKey}
                    disabled={anyMutationPending}
                    aria-busy={generateKey.isPending}
                  >
                    {generateKey.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <KeyRound className="mr-2 h-4 w-4" aria-hidden />
                    )}
                    Generate Key
                  </Button>
                </div>

                {/* Error display */}
                {uploadError && (
                  <p id="key-error" className="text-sm text-destructive" role="alert">
                    {uploadError}
                  </p>
                )}

                {/* Verify result inline badge */}
                {verifyResult === 'success' && (
                  <p className="flex items-center gap-1.5 text-sm text-green-600 dark:text-green-400">
                    <ShieldCheck className="h-4 w-4" aria-hidden />
                    Key verified — matches current encryption key.
                  </p>
                )}
                {verifyResult === 'failed' && (
                  <p className="text-sm text-destructive">
                    Verification failed — key does not match.
                  </p>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  onClick={handleUploadKey}
                  disabled={anyMutationPending || !keyInput.trim()}
                  aria-busy={uploadKey.isPending}
                >
                  {uploadKey.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                  )}
                  {uploadLabel}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleVerifyKey}
                  disabled={anyMutationPending || !keyInput.trim()}
                  aria-busy={verifyKey.isPending}
                >
                  {verifyKey.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                  )}
                  Verify Key
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
});
