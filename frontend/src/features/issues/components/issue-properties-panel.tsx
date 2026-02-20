'use client';

import { useMemo, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import { stateNameToKey } from '@/lib/issue-helpers';
import type {
  Issue,
  UpdateIssueData,
  IssueState,
  IssuePriority,
  LabelBrief,
  Cycle,
  UserBrief,
  StateBrief,
  IntegrationLink,
  NoteIssueLink,
  StateGroup,
} from '@/types';
import { useIssueStore } from '@/stores';
import { useSaveStatus, type WorkspaceMember } from '@/features/issues/hooks';
import {
  IssueStateSelect,
  IssuePrioritySelect,
  CycleSelector,
  AssigneeSelector,
  LabelSelector,
} from '@/components/issues';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { SaveStatus } from '@/components/ui/save-status';
import { LinkedPRsList } from '@/features/issues/components/linked-prs-list';
import { SourceNotesList } from '@/features/issues/components/source-notes-list';
import { EffortField } from '@/features/issues/components/effort-field';
import { FieldSaveIndicator } from '@/features/issues/components/field-save-indicator';

// ---------------------------------------------------------------------------
// State group -> IssueState mapping
// ---------------------------------------------------------------------------
const STATE_GROUP_MAP: Record<StateGroup, IssueState> = {
  backlog: 'backlog',
  unstarted: 'todo',
  started: 'in_progress',
  completed: 'done',
  cancelled: 'cancelled',
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface IssuePropertiesPanelProps {
  issue: Issue;
  workspaceId: string;
  workspaceSlug: string;
  members: WorkspaceMember[];
  labels: LabelBrief[];
  cycles: Cycle[];
  states?: StateBrief[];
  integrationLinks?: IntegrationLink[];
  noteLinks?: NoteIssueLink[];
  onUpdate: (data: UpdateIssueData) => Promise<unknown>;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Get initials from a display name for the reporter avatar. */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/** Format an ISO date string for display. */
function formatDate(iso: string): string {
  return format(new Date(iso), 'MMM d, yyyy');
}

// ---------------------------------------------------------------------------
// Sub-components: property rows
// ---------------------------------------------------------------------------

interface PropertyRowProps {
  label: string;
  fieldName?: string;
  children: React.ReactNode;
}

function PropertyRow({ label, fieldName, children }: PropertyRowProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-1">
        {children}
        {fieldName && <FieldSaveIndicator fieldName={fieldName} />}
      </div>
    </div>
  );
}

interface DatePickerFieldProps {
  label: string;
  fieldName: string;
  value: string | undefined;
  dateField: 'startDate' | 'targetDate';
  clearField: 'clearStartDate' | 'clearTargetDate';
  onUpdate: (data: UpdateIssueData) => Promise<unknown>;
  disabled?: boolean;
}

function DatePickerField({
  label,
  fieldName,
  value,
  dateField,
  clearField,
  onUpdate,
  disabled,
}: DatePickerFieldProps) {
  const { wrapMutation } = useSaveStatus(fieldName);
  const selected = value ? new Date(value) : undefined;

  const handleSelect = useCallback(
    (d: Date | undefined) => {
      if (d) {
        wrapMutation(() => onUpdate({ [dateField]: d.toISOString().split('T')[0] })).catch(
          () => {}
        );
      } else {
        wrapMutation(() => onUpdate({ [clearField]: true })).catch(() => {});
      }
    },
    [wrapMutation, onUpdate, dateField, clearField]
  );

  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              disabled={disabled}
              className={cn(
                'h-8 justify-start rounded-[10px] text-left text-sm font-normal',
                !selected && 'text-muted-foreground'
              )}
            >
              <CalendarIcon className="mr-2 size-4" />
              {selected ? format(selected, 'MMM d, yyyy') : 'Not set'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar mode="single" selected={selected} onSelect={handleSelect} />
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const IssuePropertiesPanel = observer(function IssuePropertiesPanel({
  issue,
  workspaceId: _workspaceId,
  workspaceSlug,
  members,
  labels,
  cycles,
  states = [],
  integrationLinks = [],
  noteLinks = [],
  onUpdate,
  disabled = false,
}: IssuePropertiesPanelProps) {
  const issueStore = useIssueStore();

  // Derive IssueState from StateBrief.group
  const currentIssueState = STATE_GROUP_MAP[issue.state.group] ?? 'backlog';

  // Map members -> UserBrief[] for AssigneeSelector (deduplicate by userId)
  const memberUsers = useMemo<UserBrief[]>(() => {
    const seen = new Set<string>();
    return members
      .filter((m) => {
        if (!m.userId || seen.has(m.userId)) return false;
        seen.add(m.userId);
        return true;
      })
      .map((m) => ({
        id: m.userId,
        email: m.email,
        displayName: m.fullName ?? null,
      }));
  }, [members]);

  // Assignee as UserBrief (already in correct shape)
  const assigneeUser = useMemo<UserBrief | null>(() => issue.assignee ?? null, [issue.assignee]);

  // Labels as LabelBrief[] (already in correct shape)
  const selectedLabels = useMemo<LabelBrief[]>(() => issue.labels ?? [], [issue.labels]);

  // Reporter display
  const reporterName = issue.reporter?.displayName ?? issue.reporter?.email ?? 'Unknown';

  // ---- Handlers (each wraps onUpdate with per-field save status) ----

  const { wrapMutation: wrapState } = useSaveStatus('state');
  const handleStateChange = useCallback(
    (state: IssueState) => {
      const matched = states.find(
        (s) => STATE_GROUP_MAP[s.group] === state || stateNameToKey(s.name) === state
      );
      if (matched) {
        wrapState(() => onUpdate({ stateId: matched.id })).catch(() => {});
      }
    },
    [states, wrapState, onUpdate]
  );

  const { wrapMutation: wrapPriority } = useSaveStatus('priority');
  const handlePriorityChange = useCallback(
    (priority: IssuePriority) => {
      wrapPriority(() => onUpdate({ priority })).catch(() => {});
    },
    [wrapPriority, onUpdate]
  );

  const { wrapMutation: wrapAssignee } = useSaveStatus('assignee');
  const handleAssigneeChange = useCallback(
    (user: UserBrief | null) => {
      if (user) {
        wrapAssignee(() => onUpdate({ assigneeId: user.id })).catch(() => {});
      } else {
        wrapAssignee(() => onUpdate({ clearAssignee: true })).catch(() => {});
      }
    },
    [wrapAssignee, onUpdate]
  );

  const { wrapMutation: wrapLabels } = useSaveStatus('labels');
  const handleLabelsChange = useCallback(
    (next: LabelBrief[]) => {
      wrapLabels(() => onUpdate({ labelIds: next.map((l) => l.id) })).catch(() => {});
    },
    [wrapLabels, onUpdate]
  );

  const { wrapMutation: wrapCycle } = useSaveStatus('cycle');
  const handleCycleChange = useCallback(
    (cycleId: string | null) => {
      if (cycleId) {
        wrapCycle(() => onUpdate({ cycleId })).catch(() => {});
      } else {
        wrapCycle(() => onUpdate({ clearCycle: true })).catch(() => {});
      }
    },
    [wrapCycle, onUpdate]
  );

  const { wrapMutation: wrapEstimate } = useSaveStatus('estimate');
  const handlePointsChange = useCallback(
    (points: number | undefined) => {
      if (points !== undefined) {
        wrapEstimate(() => onUpdate({ estimatePoints: points })).catch(() => {});
      } else {
        wrapEstimate(() => onUpdate({ clearEstimate: true })).catch(() => {});
      }
    },
    [wrapEstimate, onUpdate]
  );

  const { wrapMutation: wrapHours } = useSaveStatus('estimateHours');
  const handleHoursChange = useCallback(
    (hours: number | undefined) => {
      wrapHours(() => onUpdate({ estimateHours: hours })).catch(() => {});
    },
    [wrapHours, onUpdate]
  );

  return (
    <aside
      aria-label="Issue properties"
      className="flex flex-col gap-0 rounded-[14px] border border-border bg-background"
    >
      {/* ---- Properties ---- */}
      <section className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Properties
          </h3>
          <SaveStatus status={issueStore.aggregateSaveStatus} />
        </div>

        <PropertyRow label="State" fieldName="state">
          <IssueStateSelect
            value={currentIssueState}
            onChange={handleStateChange}
            disabled={disabled || states.length === 0}
            className="h-8 flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Priority" fieldName="priority">
          <IssuePrioritySelect
            value={issue.priority ?? 'none'}
            onChange={handlePriorityChange}
            disabled={disabled}
            className="h-8 flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Assignee" fieldName="assignee">
          <AssigneeSelector
            value={assigneeUser}
            members={memberUsers}
            onChange={handleAssigneeChange}
            disabled={disabled}
            className="flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Labels" fieldName="labels">
          <LabelSelector
            selectedLabels={selectedLabels}
            availableLabels={labels}
            onChange={handleLabelsChange}
            disabled={disabled}
            className="flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Cycle" fieldName="cycle">
          <CycleSelector
            value={issue.cycleId ?? null}
            onChange={handleCycleChange}
            cycles={cycles}
            disabled={disabled}
            className="h-8 flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Effort" fieldName="estimate">
          <EffortField
            estimatePoints={issue.estimatePoints ?? undefined}
            estimateHours={issue.estimateHours || undefined}
            onPointsChange={handlePointsChange}
            onHoursChange={handleHoursChange}
            disabled={disabled}
          />
        </PropertyRow>
      </section>

      <hr className="border-border" />

      {/* ---- Dates ---- */}
      <section className="space-y-3 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Dates
        </h3>

        <DatePickerField
          label="Start date"
          fieldName="startDate"
          value={issue.startDate}
          dateField="startDate"
          clearField="clearStartDate"
          onUpdate={onUpdate}
          disabled={disabled}
        />

        <DatePickerField
          label="Due date"
          fieldName="targetDate"
          value={issue.targetDate}
          dateField="targetDate"
          clearField="clearTargetDate"
          onUpdate={onUpdate}
          disabled={disabled}
        />
      </section>

      <hr className="border-border" />

      {/* ---- Details ---- */}
      <section className="space-y-3 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Details
        </h3>

        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-sm text-muted-foreground">Reporter</span>
          <div className="flex items-center gap-2">
            <span
              className="flex size-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground"
              aria-hidden="true"
            >
              {getInitials(reporterName)}
            </span>
            <span className="text-sm">{reporterName}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-sm text-muted-foreground">Created</span>
          <span className="text-sm">{formatDate(issue.createdAt)}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-sm text-muted-foreground">Updated</span>
          <span className="text-sm">{formatDate(issue.updatedAt)}</span>
        </div>
      </section>

      <hr className="border-border" />

      {/* ---- Linked Items ---- */}
      <section className="space-y-3 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Linked Items
        </h3>

        <LinkedPRsList links={integrationLinks} />
        <SourceNotesList links={noteLinks} workspaceSlug={workspaceSlug} />
      </section>
    </aside>
  );
});
