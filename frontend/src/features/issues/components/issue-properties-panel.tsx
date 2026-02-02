'use client';

import { useMemo, useCallback } from 'react';
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import type {
  Issue,
  UpdateIssueData,
  IssueState,
  IssuePriority,
  IssueType,
  Label,
  Cycle,
  User,
  StateBrief,
  IntegrationLink,
  NoteIssueLink,
  StateGroup,
} from '@/types';
import { useSaveStatus, type WorkspaceMember } from '@/features/issues/hooks';
import {
  IssueStateSelect,
  IssuePrioritySelect,
  IssueTypeSelect,
  CycleSelector,
  EstimateSelector,
  AssigneeSelector,
  LabelSelector,
} from '@/components/issues';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { SaveStatus } from '@/components/ui/save-status';
import { LinkedPRsList } from '@/features/issues/components/linked-prs-list';
import { SourceNotesList } from '@/features/issues/components/source-notes-list';

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
  labels: Label[];
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

/** Map UserBrief to User (AssigneeSelector expects User). */
function toUser(brief: { id: string; email: string; displayName: string | null }): User {
  return {
    id: brief.id,
    email: brief.email,
    name: brief.displayName ?? brief.email,
    avatarUrl: undefined,
    createdAt: '',
    updatedAt: '',
  };
}

/** Map LabelBrief to Label (LabelSelector expects Label). */
function toLabel(brief: { id: string; name: string; color: string }, projectId: string): Label {
  return { id: brief.id, name: brief.name, color: brief.color, projectId };
}

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
  fieldName: string;
  children: React.ReactNode;
}

function PropertyRow({ label, fieldName, children }: PropertyRowProps) {
  const { status } = useSaveStatus(fieldName);

  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {children}
        <SaveStatus status={status} className="shrink-0" />
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
  const { status, wrapMutation } = useSaveStatus(fieldName);
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
        <SaveStatus status={status} className="shrink-0" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function IssuePropertiesPanel({
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
  // Derive IssueState from StateBrief.group
  const currentIssueState = STATE_GROUP_MAP[issue.state.group] ?? 'backlog';

  // Map members -> User[] for AssigneeSelector
  const memberUsers = useMemo<User[]>(() => members.map((m) => m.user), [members]);

  // Map issue.assignee (UserBrief | null) -> User | null
  const assigneeUser = useMemo<User | null>(
    () => (issue.assignee ? toUser(issue.assignee) : null),
    [issue.assignee]
  );

  // Map issue.labels (LabelBrief[]) -> Label[]
  const selectedLabels = useMemo<Label[]>(
    () => (issue.labels ?? []).map((lb) => toLabel(lb, issue.projectId)),
    [issue.labels, issue.projectId]
  );

  // Reporter display
  const reporterName = issue.reporter?.displayName ?? issue.reporter?.email ?? 'Unknown';

  // ---- Handlers (each wraps onUpdate with per-field save status) ----

  const { wrapMutation: wrapState } = useSaveStatus('state');
  const handleStateChange = useCallback(
    (state: IssueState) => {
      const matched = states.find(
        (s) =>
          STATE_GROUP_MAP[s.group] === state || s.name.toLowerCase().replace(/\s+/g, '_') === state
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

  useSaveStatus('type');
  const handleTypeChange = useCallback((_type: IssueType) => {
    // UpdateIssueData does not expose a `type` field in the current schema.
    // This is a visual-only selector until the API supports type updates.
    void _type;
  }, []);

  const { wrapMutation: wrapAssignee } = useSaveStatus('assignee');
  const handleAssigneeChange = useCallback(
    (user: User | null) => {
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
    (next: Label[]) => {
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
  const handleEstimateChange = useCallback(
    (points: number | undefined) => {
      if (points !== undefined) {
        wrapEstimate(() => onUpdate({ estimatePoints: points })).catch(() => {});
      } else {
        wrapEstimate(() => onUpdate({ clearEstimate: true })).catch(() => {});
      }
    },
    [wrapEstimate, onUpdate]
  );

  return (
    <aside
      aria-label="Issue properties"
      className="flex flex-col gap-0 rounded-[14px] border border-border bg-background"
    >
      {/* ---- Properties ---- */}
      <section className="space-y-3 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Properties
        </h3>

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
            value={issue.priority}
            onChange={handlePriorityChange}
            disabled={disabled}
            className="h-8 flex-1"
          />
        </PropertyRow>

        <PropertyRow label="Type" fieldName="type">
          <IssueTypeSelect
            value={issue.type}
            onChange={handleTypeChange}
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

        <PropertyRow label="Estimate" fieldName="estimate">
          <EstimateSelector
            value={issue.estimatePoints}
            onChange={handleEstimateChange}
            disabled={disabled}
            className="h-8 flex-1"
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
}
