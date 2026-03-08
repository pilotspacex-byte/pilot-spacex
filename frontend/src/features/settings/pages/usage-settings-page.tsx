/**
 * UsageSettingsPage - Workspace storage and rate limit quota display.
 *
 * TENANT-03: Usage bars (storage + rate limits) with owner-editable quota fields.
 * Non-owner members see read-only values.
 *
 * Plain React (NO observer()) — TanStack Query for all data.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';
import { ApiError } from '@/services/api';
import { useWorkspaceQuota, useUpdateWorkspaceQuota } from '../hooks/use-workspace-quota';
import type { QuotaStatus } from '../hooks/use-workspace-quota';

// ---- Helpers ----

/** System defaults shown when quota fields are null. */
const SYSTEM_DEFAULT_STANDARD_RPM = 1000;
const SYSTEM_DEFAULT_AI_RPM = 100;

function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.detail ?? err.message;
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred.';
}

/**
 * Compute storage progress percentage (0-100).
 * Returns 0 if quota is null (unlimited).
 */
function computeStoragePct(usedMb: number, quotaMb: number | null): number {
  if (!quotaMb || quotaMb <= 0) return 0;
  return Math.min(100, (usedMb / quotaMb) * 100);
}

/**
 * CSS class for progress bar indicator based on usage percentage.
 * The Progress component uses bg-primary by default; override for warnings.
 */
function storageBarClass(pct: number): string {
  if (pct >= 100) return '[&>[data-slot=progress-indicator]]:bg-destructive';
  if (pct >= 80) return '[&>[data-slot=progress-indicator]]:bg-amber-500';
  return '';
}

// ---- Sub-components ----

function QuotaSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-2 w-full" />
      <Skeleton className="h-4 w-48" />
    </div>
  );
}

function StorageBar({ quota }: { quota: QuotaStatus }) {
  const pct = computeStoragePct(quota.storage_used_mb, quota.storage_quota_mb);
  const barClass = storageBarClass(pct);
  const isUnlimited = !quota.storage_quota_mb;

  return (
    <div className="space-y-2">
      {!isUnlimited && <Progress value={pct} className={`h-2 ${barClass}`} />}
      <p className="text-sm text-muted-foreground">
        {quota.storage_used_mb.toFixed(2)} MB used
        {quota.storage_quota_mb ? ` of ${quota.storage_quota_mb} MB` : ' — no storage limit set'}
        {pct >= 80 && pct < 100 && (
          <span className="ml-2 text-amber-600 dark:text-amber-400 font-medium">
            ({pct.toFixed(0)}% — approaching limit)
          </span>
        )}
        {pct >= 100 && <span className="ml-2 text-destructive font-medium">(Quota exceeded)</span>}
      </p>
    </div>
  );
}

// ---- Owner Edit Form ----

interface QuotaFormState {
  storage_quota_mb: string;
  rate_limit_standard_rpm: string;
  rate_limit_ai_rpm: string;
}

function parseNullableInt(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === '') return null;
  const parsed = parseInt(trimmed, 10);
  return isNaN(parsed) || parsed < 1 ? null : parsed;
}

function quotaToFormState(quota: QuotaStatus): QuotaFormState {
  return {
    storage_quota_mb: quota.storage_quota_mb !== null ? String(quota.storage_quota_mb) : '',
    rate_limit_standard_rpm:
      quota.rate_limit_standard_rpm !== null ? String(quota.rate_limit_standard_rpm) : '',
    rate_limit_ai_rpm: quota.rate_limit_ai_rpm !== null ? String(quota.rate_limit_ai_rpm) : '',
  };
}

function OwnerQuotaForm({ quota, workspaceSlug }: { quota: QuotaStatus; workspaceSlug: string }) {
  const updateQuota = useUpdateWorkspaceQuota(workspaceSlug);
  const [form, setForm] = React.useState<QuotaFormState>(() => quotaToFormState(quota));
  const [saveError, setSaveError] = React.useState<string | null>(null);

  // Sync form state if quota data refreshes (e.g., after invalidation).
  // Destructure to stable primitives so effect deps are scalars, not object reference.
  const { storage_quota_mb, rate_limit_standard_rpm, rate_limit_ai_rpm } = quota;
  React.useEffect(() => {
    setForm(quotaToFormState(quota));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storage_quota_mb, rate_limit_standard_rpm, rate_limit_ai_rpm]);

  const handleChange =
    (field: keyof QuotaFormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
      setSaveError(null);
    };

  const handleSave = async () => {
    setSaveError(null);
    try {
      await updateQuota.mutateAsync({
        storage_quota_mb: parseNullableInt(form.storage_quota_mb),
        rate_limit_standard_rpm: parseNullableInt(form.rate_limit_standard_rpm),
        rate_limit_ai_rpm: parseNullableInt(form.rate_limit_ai_rpm),
      });
      toast.success('Quota settings updated');
    } catch (err) {
      setSaveError(extractErrorMessage(err));
    }
  };

  return (
    <div className="space-y-5">
      {/* Storage quota field */}
      <div className="space-y-2">
        <Label htmlFor="storage-quota-mb">Storage Quota (MB)</Label>
        <Input
          id="storage-quota-mb"
          type="number"
          min="1"
          value={form.storage_quota_mb}
          onChange={handleChange('storage_quota_mb')}
          placeholder="Leave empty for Unlimited"
          className="max-w-xs"
          disabled={updateQuota.isPending}
          aria-describedby="storage-quota-hint"
        />
        <p id="storage-quota-hint" className="text-xs text-muted-foreground">
          Leave empty to allow unlimited storage.
        </p>
      </div>

      {/* Standard RPM field */}
      <div className="space-y-2">
        <Label htmlFor="standard-rpm">Standard API Rate Limit (RPM)</Label>
        <Input
          id="standard-rpm"
          type="number"
          min="1"
          value={form.rate_limit_standard_rpm}
          onChange={handleChange('rate_limit_standard_rpm')}
          placeholder={`Leave empty for system default (${SYSTEM_DEFAULT_STANDARD_RPM} RPM)`}
          className="max-w-xs"
          disabled={updateQuota.isPending}
          aria-describedby="standard-rpm-hint"
        />
        <p id="standard-rpm-hint" className="text-xs text-muted-foreground">
          Leave empty to use the system default of {SYSTEM_DEFAULT_STANDARD_RPM} RPM.
        </p>
      </div>

      {/* AI RPM field */}
      <div className="space-y-2">
        <Label htmlFor="ai-rpm">AI API Rate Limit (RPM)</Label>
        <Input
          id="ai-rpm"
          type="number"
          min="1"
          value={form.rate_limit_ai_rpm}
          onChange={handleChange('rate_limit_ai_rpm')}
          placeholder={`Leave empty for system default (${SYSTEM_DEFAULT_AI_RPM} RPM)`}
          className="max-w-xs"
          disabled={updateQuota.isPending}
          aria-describedby="ai-rpm-hint"
        />
        <p id="ai-rpm-hint" className="text-xs text-muted-foreground">
          Leave empty to use the system default of {SYSTEM_DEFAULT_AI_RPM} RPM.
        </p>
      </div>

      {/* Error */}
      {saveError && (
        <p className="text-sm text-destructive" role="alert">
          {saveError}
        </p>
      )}

      {/* Save button */}
      <Button
        type="button"
        onClick={handleSave}
        disabled={updateQuota.isPending}
        aria-busy={updateQuota.isPending}
      >
        {updateQuota.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
        Save Changes
      </Button>
    </div>
  );
}

// ---- Read-only Rate Limit Display ----

function RateLimitReadOnly({ quota }: { quota: QuotaStatus }) {
  const standardRpm =
    quota.rate_limit_standard_rpm !== null
      ? `${quota.rate_limit_standard_rpm} RPM`
      : `${SYSTEM_DEFAULT_STANDARD_RPM} RPM (system default)`;
  const aiRpm =
    quota.rate_limit_ai_rpm !== null
      ? `${quota.rate_limit_ai_rpm} RPM`
      : `${SYSTEM_DEFAULT_AI_RPM} RPM (system default)`;

  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
      <dt className="text-muted-foreground">Standard API</dt>
      <dd className="font-medium">{standardRpm}</dd>
      <dt className="text-muted-foreground">AI API</dt>
      <dd className="font-medium">{aiRpm}</dd>
      <dt className="text-muted-foreground">Storage Quota</dt>
      <dd className="font-medium">
        {quota.storage_quota_mb !== null ? `${quota.storage_quota_mb} MB` : 'Unlimited'}
      </dd>
    </dl>
  );
}

// ---- Main Component ----

export const UsageSettingsPage = observer(function UsageSettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const isOwner = workspaceStore.isOwner;

  const { data: quota, isLoading, error } = useWorkspaceQuota(workspaceSlug);

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Usage &amp; Quotas</h1>
          <p className="text-sm text-muted-foreground">
            Current usage and configurable limits for this workspace.
          </p>
        </div>

        {/* Storage Card */}
        <Card>
          <CardHeader>
            <CardTitle>Storage Usage</CardTitle>
            <CardDescription>
              Disk space consumed by notes, attachments, and other workspace data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <QuotaSkeleton />
            ) : error ? (
              <Alert variant="destructive">
                <AlertTitle>Failed to load usage data</AlertTitle>
                <AlertDescription>{extractErrorMessage(error)}</AlertDescription>
              </Alert>
            ) : quota ? (
              <StorageBar quota={quota} />
            ) : null}
          </CardContent>
        </Card>

        {/* Rate Limits Card */}
        <Card>
          <CardHeader>
            <CardTitle>API Rate Limits</CardTitle>
            <CardDescription>
              Requests-per-minute caps applied to this workspace.
              {isOwner && ' Edit to override the system defaults.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <QuotaSkeleton />
            ) : error ? (
              <Alert variant="destructive">
                <AlertTitle>Failed to load quota settings</AlertTitle>
                <AlertDescription>{extractErrorMessage(error)}</AlertDescription>
              </Alert>
            ) : quota ? (
              isOwner ? (
                <OwnerQuotaForm quota={quota} workspaceSlug={workspaceSlug} />
              ) : (
                <RateLimitReadOnly quota={quota} />
              )
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
});
