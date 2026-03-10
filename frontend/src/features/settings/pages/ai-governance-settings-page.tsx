/**
 * AIGovernanceSettingsPage — Policy matrix for AI action approval requirements.
 *
 * AIGOV-02: Per-role policy configuration. Each cell toggles Auto / Approval for a given
 * (action_type, role) combination. ALWAYS_REQUIRE actions are locked to Always in all cells.
 * Owner column is greyed-out and non-editable (owners always auto-execute).
 *
 * Plain React component — NOT observer().
 * Data fetching via TanStack Query. Mutations call PUT endpoint per cell change.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { apiClient } from '@/services/api';

// ---- Types ----

interface PolicyRow {
  role: string;
  action_type: string;
  requires_approval: boolean;
}

/** Map from "ROLE:ACTION_TYPE" -> requires_approval */
type PolicyMap = Map<string, boolean>;

function policyKey(role: string, actionType: string): string {
  return `${role.toUpperCase()}:${actionType}`;
}

// ---- Action groups ----

interface ActionGroup {
  label: string;
  actions: string[];
}

/** Actions that are ALWAYS locked to approval regardless of policy. */
const ALWAYS_REQUIRE_ACTIONS = new Set(['DELETE_ISSUE', 'DELETE_NOTE', 'MERGE_PR', 'BULK_DELETE']);

const ACTION_GROUPS: ActionGroup[] = [
  {
    label: 'Content Actions',
    actions: ['CREATE_ISSUE', 'UPDATE_ISSUE', 'CREATE_NOTE', 'GENERATE_CONTENT'],
  },
  {
    label: 'Code Actions',
    actions: ['CREATE_PR', 'SUGGEST_CODE', 'REVIEW_PR'],
  },
  {
    label: 'Administrative',
    actions: ['BULK_UPDATE', 'UPDATE_SETTINGS'],
  },
  {
    label: 'Always Required',
    actions: ['DELETE_ISSUE', 'DELETE_NOTE', 'MERGE_PR', 'BULK_DELETE'],
  },
];

/** Roles displayed as columns. OWNER column is read-only. */
const ROLES = ['OWNER', 'ADMIN', 'MEMBER', 'GUEST'] as const;
type Role = (typeof ROLES)[number];

function formatActionType(actionType: string): string {
  return actionType
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// ---- TanStack Query hooks ----

function useAIPolicy(workspaceSlug: string) {
  return useQuery<PolicyRow[]>({
    queryKey: ['ai-policy', workspaceSlug],
    queryFn: () => apiClient.get<PolicyRow[]>(`/workspaces/${workspaceSlug}/settings/ai-policy`),
    enabled: Boolean(workspaceSlug),
  });
}

interface PolicyMutationInput {
  role: Role;
  action_type: string;
  requires_approval: boolean;
}

function useSetAIPolicy(workspaceSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ role, action_type, requires_approval }: PolicyMutationInput) =>
      apiClient.put<PolicyRow>(
        `/workspaces/${workspaceSlug}/settings/ai-policy/${role}/${action_type}`,
        { requires_approval }
      ),
    onMutate: async ({ role, action_type, requires_approval }) => {
      // Optimistic update: flip the cell immediately
      await queryClient.cancelQueries({ queryKey: ['ai-policy', workspaceSlug] });
      const previous = queryClient.getQueryData<PolicyRow[]>(['ai-policy', workspaceSlug]);

      queryClient.setQueryData<PolicyRow[]>(['ai-policy', workspaceSlug], (old) => {
        if (!old) return old;
        const key = policyKey(role, action_type);
        const existing = old.find((r) => policyKey(r.role, r.action_type) === key);
        if (existing) {
          return old.map((r) =>
            policyKey(r.role, r.action_type) === key ? { ...r, requires_approval } : r
          );
        }
        return [...old, { role: role.toUpperCase(), action_type, requires_approval }];
      });

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back optimistic update
      if (context?.previous) {
        queryClient.setQueryData(['ai-policy', workspaceSlug], context.previous);
      }
      toast.error('Failed to save policy');
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ai-policy', workspaceSlug] });
    },
  });
}

// ---- PolicyCell ----

interface PolicyCellProps {
  role: Role;
  actionType: string;
  policyMap: PolicyMap;
  isAlwaysRequire: boolean;
  isLoading: boolean;
  onToggle: (role: Role, actionType: string, requiresApproval: boolean) => void;
}

function PolicyCell({
  role,
  actionType,
  policyMap,
  isAlwaysRequire,
  isLoading,
  onToggle,
}: PolicyCellProps) {
  if (isAlwaysRequire) {
    return (
      <TableCell className="text-center">
        <Badge variant="destructive" className="text-xs">
          Always
        </Badge>
      </TableCell>
    );
  }

  if (role === 'OWNER') {
    return (
      <TableCell className="text-center" title="Owners always auto-execute AI actions">
        <Badge variant="secondary" className="text-xs text-muted-foreground">
          Auto
        </Badge>
      </TableCell>
    );
  }

  if (isLoading) {
    return (
      <TableCell className="text-center">
        <Skeleton className="h-5 w-10 mx-auto" />
      </TableCell>
    );
  }

  // Absence of a policy row = uses hardcoded ApprovalService defaults.
  // We display what the current value is (false = auto, true = requires approval).
  const requiresApproval = policyMap.get(policyKey(role, actionType)) ?? false;

  return (
    <TableCell className="text-center">
      <div className="flex items-center justify-center gap-1.5">
        <Switch
          checked={requiresApproval}
          onCheckedChange={(checked) => onToggle(role, actionType, checked)}
          aria-label={`${role} ${actionType}: ${requiresApproval ? 'approval required' : 'auto'}`}
          className="data-[state=checked]:bg-amber-500"
        />
        <span className="text-xs text-muted-foreground min-w-[52px]">
          {requiresApproval ? 'Approval' : 'Auto'}
        </span>
      </div>
    </TableCell>
  );
}

// ---- PolicyRow sub-component ----

interface PolicyRowProps {
  actionType: string;
  policyMap: PolicyMap;
  isAlwaysRequire: boolean;
  isLoading: boolean;
  onToggle: (role: Role, actionType: string, requiresApproval: boolean) => void;
}

function PolicyRowItem({
  actionType,
  policyMap,
  isAlwaysRequire,
  isLoading,
  onToggle,
}: PolicyRowProps) {
  return (
    <TableRow>
      <TableCell className="font-medium text-sm">{formatActionType(actionType)}</TableCell>
      {ROLES.map((role) => (
        <PolicyCell
          key={role}
          role={role}
          actionType={actionType}
          policyMap={policyMap}
          isAlwaysRequire={isAlwaysRequire}
          isLoading={isLoading}
          onToggle={onToggle}
        />
      ))}
    </TableRow>
  );
}

// ---- Main Component ----

export function AIGovernanceSettingsPage() {
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;

  const { data: policyRows, isLoading } = useAIPolicy(workspaceSlug);
  const setPolicy = useSetAIPolicy(workspaceSlug);

  // Build lookup map: "ROLE:ACTION_TYPE" -> requires_approval
  const policyMap = React.useMemo<PolicyMap>(() => {
    const map = new Map<string, boolean>();
    if (!policyRows) return map;
    for (const row of policyRows) {
      map.set(policyKey(row.role, row.action_type), row.requires_approval);
    }
    return map;
  }, [policyRows]);

  const handleToggle = (role: Role, actionType: string, requiresApproval: boolean) => {
    setPolicy.mutate({ role, action_type: actionType, requires_approval: requiresApproval });
  };

  return (
    <div className="max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
            <ShieldCheck className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="space-y-0.5">
            <h1 className="text-2xl font-semibold tracking-tight">AI Governance</h1>
            <p className="text-sm text-muted-foreground">
              Configure which AI actions require human approval per role. Changes take effect
              immediately for new AI-initiated actions.
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Switch checked={false} className="h-4 w-7 pointer-events-none" aria-hidden />
            <span>Auto — AI executes without review</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Switch
              checked
              className="h-4 w-7 pointer-events-none data-[state=checked]:bg-amber-500"
              aria-hidden
            />
            <span>Approval — requires human review</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="destructive" className="text-xs">
              Always
            </Badge>
            <span>locked — always requires approval</span>
          </div>
        </div>

        {/* Policy Matrix */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Approval Policy Matrix</CardTitle>
            <CardDescription>
              Owner column is non-editable — owners always auto-execute all AI actions.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-48">Action</TableHead>
                  {ROLES.map((role) => (
                    <TableHead
                      key={role}
                      className={`text-center w-32 ${role === 'OWNER' ? 'text-muted-foreground' : ''}`}
                    >
                      {role.charAt(0) + role.slice(1).toLowerCase()}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {ACTION_GROUPS.map((group) => (
                  <React.Fragment key={group.label}>
                    {/* Group header row */}
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="font-semibold text-xs uppercase tracking-wide bg-muted/50 text-muted-foreground py-2"
                      >
                        {group.label}
                      </TableCell>
                    </TableRow>
                    {/* Action rows */}
                    {group.actions.map((action) => (
                      <PolicyRowItem
                        key={action}
                        actionType={action}
                        policyMap={policyMap}
                        isAlwaysRequire={ALWAYS_REQUIRE_ACTIONS.has(action)}
                        isLoading={isLoading}
                        onToggle={handleToggle}
                      />
                    ))}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Owner note */}
        <p className="text-xs text-muted-foreground">
          Owner-role policies are not configurable. Owners always have auto-execute authority over
          all AI actions. To restrict an owner, change their workspace role.
        </p>
      </div>
    </div>
  );
}
