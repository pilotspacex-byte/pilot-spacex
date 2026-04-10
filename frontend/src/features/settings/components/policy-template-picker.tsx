/**
 * PolicyTemplatePicker — apply one of three preset permission templates
 * (conservative / standard / trusted) with a confirmation dialog.
 *
 * Phase 69 DD-003.
 */

'use client';

import * as React from 'react';
import { Shield, ShieldCheck, ShieldAlert } from 'lucide-react';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useApplyPolicyTemplate } from '../hooks/use-ai-permissions';
import type { PolicyTemplate } from '../types/ai-permissions';

interface PolicyTemplatePickerProps {
  workspaceId: string | undefined;
}

const TEMPLATES: Array<{
  id: PolicyTemplate;
  label: string;
  description: string;
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  {
    id: 'conservative',
    label: 'Conservative',
    description: 'Maximum oversight. All non-trivial tools require explicit approval.',
    Icon: ShieldAlert,
  },
  {
    id: 'standard',
    label: 'Standard',
    description: 'Balanced defaults. Read-only tools auto-approved, write tools require ask.',
    Icon: Shield,
  },
  {
    id: 'trusted',
    label: 'Trusted',
    description: 'Minimal friction. Most tools auto-approved; only destructive ops gated.',
    Icon: ShieldCheck,
  },
];

export function PolicyTemplatePicker({ workspaceId }: PolicyTemplatePickerProps) {
  const apply = useApplyPolicyTemplate(workspaceId);
  const [pending, setPending] = React.useState<PolicyTemplate | null>(null);

  const handleConfirm = () => {
    if (!pending) return;
    apply.mutate(pending, { onSettled: () => setPending(null) });
  };

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Policy Templates</CardTitle>
        <CardDescription>
          Apply a preset to overwrite all per-tool permissions in one action.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-3">
          {TEMPLATES.map(({ id, label, description, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setPending(id)}
              disabled={apply.isPending}
              className="group flex flex-col items-start gap-2 rounded-lg border bg-card p-3 text-left transition-colors hover:border-primary/50 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              aria-label={`Apply ${label} policy template`}
              data-testid={`template-${id}`}
            >
              <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
              <div className="text-sm font-semibold">{label}</div>
              <div className="text-xs text-muted-foreground">{description}</div>
            </button>
          ))}
        </div>
      </CardContent>

      <AlertDialog open={pending !== null} onOpenChange={(open) => !open && setPending(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Apply &quot;{pending}&quot; policy template?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will overwrite all per-tool permissions for this workspace. Existing custom
              settings will be replaced. This action is logged in the audit log.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} disabled={apply.isPending}>
              {apply.isPending ? 'Applying…' : 'Apply template'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
