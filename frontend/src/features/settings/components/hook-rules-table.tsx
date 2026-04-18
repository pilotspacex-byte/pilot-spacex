/**
 * HookRulesTable -- CRUD table for workspace hook rules (Phase 83).
 *
 * Displays hook rules in a table with inline enable/disable toggle.
 * Create and edit use a shared dialog form. Delete uses a confirmation dialog.
 * All mutations use TanStack Query hooks with cache invalidation.
 */

'use client';

import * as React from 'react';
import { Pencil, Plus, Shield, ShieldAlert, ShieldOff, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  useCreateHookRule,
  useDeleteHookRule,
  useToggleHookRule,
  useUpdateHookRule,
  useWorkspaceHooks,
} from '../hooks/use-workspace-hooks';
import type { CreateHookRuleInput, HookAction, HookEventType, HookRule } from '../types/hook-rules';

// ---- Constants ----

const ACTION_META: Record<
  HookAction,
  { label: string; Icon: React.ComponentType<{ className?: string }>; badgeClass: string }
> = {
  allow: {
    label: 'Allow',
    Icon: Shield,
    badgeClass: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30',
  },
  deny: {
    label: 'Deny',
    Icon: ShieldOff,
    badgeClass: 'bg-destructive/10 text-destructive border-destructive/30',
  },
  require_approval: {
    label: 'Require Approval',
    Icon: ShieldAlert,
    badgeClass: 'bg-amber-500/10 text-amber-600 border-amber-500/30',
  },
};

const EVENT_TYPE_OPTIONS: { value: HookEventType; label: string }[] = [
  { value: 'PreToolUse', label: 'PreToolUse' },
  { value: 'PostToolUse', label: 'PostToolUse' },
  { value: 'Stop', label: 'Stop' },
];

const ACTION_OPTIONS: { value: HookAction; label: string }[] = [
  { value: 'allow', label: 'Allow' },
  { value: 'deny', label: 'Deny' },
  { value: 'require_approval', label: 'Require Approval' },
];

// ---- Props ----

interface HookRulesTableProps {
  workspaceId: string | undefined;
}

// ---- Form state ----

interface HookRuleFormState {
  name: string;
  toolPattern: string;
  action: HookAction;
  eventType: HookEventType;
  priority: string;
  description: string;
}

const EMPTY_FORM: HookRuleFormState = {
  name: '',
  toolPattern: '',
  action: 'deny',
  eventType: 'PreToolUse',
  priority: '100',
  description: '',
};

function formFromRule(rule: HookRule): HookRuleFormState {
  return {
    name: rule.name,
    toolPattern: rule.toolPattern,
    action: rule.action,
    eventType: rule.eventType,
    priority: String(rule.priority),
    description: rule.description ?? '',
  };
}

// ---- Component ----

export function HookRulesTable({ workspaceId }: HookRulesTableProps) {
  const { data, isLoading, error, refetch } = useWorkspaceHooks(workspaceId);
  const createMutation = useCreateHookRule(workspaceId);
  const updateMutation = useUpdateHookRule(workspaceId);
  const deleteMutation = useDeleteHookRule(workspaceId);
  const toggleMutation = useToggleHookRule(workspaceId);

  // Dialog state
  const [formOpen, setFormOpen] = React.useState(false);
  const [editingRule, setEditingRule] = React.useState<HookRule | null>(null);
  const [form, setForm] = React.useState<HookRuleFormState>(EMPTY_FORM);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = React.useState<HookRule | null>(null);

  const rules = data?.rules ?? [];

  // ---- Handlers ----

  const openCreate = () => {
    setEditingRule(null);
    setForm(EMPTY_FORM);
    setFormOpen(true);
  };

  const openEdit = (rule: HookRule) => {
    setEditingRule(rule);
    setForm(formFromRule(rule));
    setFormOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const priority = Math.max(0, Math.min(9999, parseInt(form.priority, 10) || 100));
    const payload: CreateHookRuleInput = {
      name: form.name.trim(),
      toolPattern: form.toolPattern.trim(),
      action: form.action,
      eventType: form.eventType,
      priority,
      description: form.description.trim() || undefined,
    };

    if (editingRule) {
      updateMutation.mutate(
        { hookId: editingRule.id, ...payload },
        { onSuccess: () => setFormOpen(false) }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => setFormOpen(false),
      });
    }
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
    });
  };

  const handleToggle = (rule: HookRule) => {
    toggleMutation.mutate({ hookId: rule.id, isEnabled: !rule.isEnabled });
  };

  const updateField = <K extends keyof HookRuleFormState>(
    field: K,
    value: HookRuleFormState[K]
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="text-base">Hook Rules</CardTitle>
              <CardDescription>
                Declarative rules that govern AI tool behavior. Rules are evaluated in
                priority order (lowest number first). First matching rule wins.
              </CardDescription>
            </div>
            <Button size="sm" onClick={openCreate}>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-destructive" role="alert">
              <p>
                Failed to load hook rules:{' '}
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
              <Button variant="ghost" size="sm" className="mt-2" onClick={() => void refetch()}>
                Retry
              </Button>
            </div>
          ) : rules.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No hook rules configured. Create a rule to govern AI tool behavior.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Priority</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Tool Pattern</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead className="w-28">Event Type</TableHead>
                  <TableHead className="w-20">Enabled</TableHead>
                  <TableHead className="w-20 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <HookRuleRow
                    key={rule.id}
                    rule={rule}
                    onEdit={openEdit}
                    onDelete={setDeleteTarget}
                    onToggle={handleToggle}
                    isToggling={
                      toggleMutation.isPending &&
                      toggleMutation.variables?.hookId === rule.id
                    }
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>{editingRule ? 'Edit Hook Rule' : 'Create Hook Rule'}</DialogTitle>
              <DialogDescription>
                {editingRule
                  ? 'Update the hook rule configuration.'
                  : 'Define a new rule to govern AI tool behavior.'}
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4 grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="hook-name">Name</Label>
                <Input
                  id="hook-name"
                  value={form.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  placeholder="Block destructive tools"
                  maxLength={128}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="hook-pattern">Tool Pattern</Label>
                <Input
                  id="hook-pattern"
                  value={form.toolPattern}
                  onChange={(e) => updateField('toolPattern', e.target.value)}
                  placeholder="delete_* or /^create_.*/ or exact_tool_name"
                  maxLength={256}
                  required
                  className="font-mono text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="hook-action">Action</Label>
                  <Select
                    value={form.action}
                    onValueChange={(v) => updateField('action', v as HookAction)}
                  >
                    <SelectTrigger id="hook-action">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTION_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="hook-event">Event Type</Label>
                  <Select
                    value={form.eventType}
                    onValueChange={(v) => updateField('eventType', v as HookEventType)}
                  >
                    <SelectTrigger id="hook-event">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {EVENT_TYPE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="hook-priority">Priority</Label>
                <Input
                  id="hook-priority"
                  type="number"
                  value={form.priority}
                  onChange={(e) => updateField('priority', e.target.value)}
                  min={0}
                  max={9999}
                  placeholder="100"
                />
                <p className="text-xs text-muted-foreground">
                  Lower numbers are evaluated first. Default is 100.
                </p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="hook-description">Description (optional)</Label>
                <Input
                  id="hook-description"
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  placeholder="Why this rule exists"
                  maxLength={512}
                />
              </div>
            </div>
            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting
                  ? 'Saving...'
                  : editingRule
                    ? 'Save Changes'
                    : 'Create Rule'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Hook Rule</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the hook rule &ldquo;{deleteTarget?.name}&rdquo;?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ---- Row sub-component ----

interface HookRuleRowProps {
  rule: HookRule;
  onEdit: (rule: HookRule) => void;
  onDelete: (rule: HookRule) => void;
  onToggle: (rule: HookRule) => void;
  isToggling: boolean;
}

function HookRuleRow({ rule, onEdit, onDelete, onToggle, isToggling }: HookRuleRowProps) {
  const meta = ACTION_META[rule.action];

  return (
    <TableRow className={!rule.isEnabled ? 'opacity-50' : undefined}>
      <TableCell className="text-center text-sm tabular-nums text-muted-foreground">
        {rule.priority}
      </TableCell>
      <TableCell className="font-medium text-sm">{rule.name}</TableCell>
      <TableCell>
        <Badge variant="outline" className="font-mono text-xs">
          {rule.toolPattern}
        </Badge>
      </TableCell>
      <TableCell>
        <Badge variant="outline" className={meta.badgeClass}>
          <meta.Icon className="mr-1 h-3 w-3" />
          {meta.label}
        </Badge>
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">{rule.eventType}</TableCell>
      <TableCell>
        <Switch
          checked={rule.isEnabled}
          onCheckedChange={() => onToggle(rule)}
          disabled={isToggling}
          aria-label={`${rule.isEnabled ? 'Disable' : 'Enable'} rule "${rule.name}"`}
        />
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => onEdit(rule)}
            aria-label={`Edit rule "${rule.name}"`}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
            onClick={() => onDelete(rule)}
            aria-label={`Delete rule "${rule.name}"`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}
