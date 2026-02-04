'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, Loader2, CheckCircle2, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { IssuePrioritySelect } from './IssuePrioritySelect';
import { IssueStateSelect } from './IssueStateSelect';
import { LabelSelector } from './LabelSelector';
import { AssigneeSelector } from './AssigneeSelector';
import { DuplicateWarning } from './DuplicateWarning';
import type {
  Issue,
  CreateIssueData,
  UpdateIssueData,
  IssueState,
  IssuePriority,
  IssueType,
  LabelBrief,
  UserBrief,
} from '@/types';
import type {
  EnhancementSuggestion,
  DuplicateCheckResult,
  AssigneeRecommendation,
} from '@/stores/features/issues/IssueStore';
import { stateNameToKey } from '@/lib/issue-helpers';

export interface IssueModalProps {
  /** Whether modal is open */
  open: boolean;
  /** Called when modal should close */
  onOpenChange: (open: boolean) => void;
  /** Existing issue for editing (null for create) */
  issue?: Issue | null;
  /** Default state for new issues */
  defaultState?: IssueState;
  /** Available labels */
  availableLabels: LabelBrief[];
  /** Team members for assignment */
  teamMembers: UserBrief[];
  /** Current project ID */
  projectId: string;
  /** AI enhancement suggestion */
  enhancementSuggestion?: EnhancementSuggestion | null;
  /** Duplicate check result */
  duplicateResult?: DuplicateCheckResult | null;
  /** Assignee recommendations */
  assigneeRecommendations?: AssigneeRecommendation[];
  /** Whether AI enhancement is loading */
  isLoadingEnhancement?: boolean;
  /** Whether duplicate check is loading */
  isCheckingDuplicates?: boolean;
  /** Called to request AI enhancement */
  onRequestEnhancement?: (title: string, description: string | null) => void;
  /** Called to check for duplicates */
  onCheckDuplicates?: (title: string, description: string | null) => void;
  /** Called to get assignee recommendations */
  onRequestAssigneeRecommendations?: (labelNames: string[]) => void;
  /** Called when saving the issue */
  onSave: (data: CreateIssueData | UpdateIssueData) => Promise<Issue | null>;
  /** Called when creating a new label */
  onCreateLabel?: (name: string) => Promise<LabelBrief>;
  /** Called when viewing a duplicate issue */
  onViewDuplicate?: (issueId: string) => void;
  /** Called to navigate to the created/edited issue detail page */
  onOpenIssue?: (issue: Issue) => void;
  /** Called to record AI suggestion decision */
  onRecordDecision?: (
    suggestionType: 'label' | 'priority' | 'assignee' | 'title' | 'description',
    accepted: boolean
  ) => void;
}

/**
 * IssueModal provides a form for creating/editing issues.
 * Integrates with AI for enhancement, duplicate detection, and recommendations.
 */
export const IssueModal = observer(function IssueModal({
  open,
  onOpenChange,
  issue,
  defaultState = 'backlog',
  availableLabels,
  teamMembers,
  projectId,
  enhancementSuggestion,
  duplicateResult,
  assigneeRecommendations = [],
  isLoadingEnhancement = false,
  // isCheckingDuplicates is unused but kept for future loading indicator
  isCheckingDuplicates: _isCheckingDuplicates = false,
  onRequestEnhancement,
  onCheckDuplicates,
  onRequestAssigneeRecommendations,
  onSave,
  onCreateLabel,
  onViewDuplicate,
  onOpenIssue,
  onRecordDecision,
}: IssueModalProps) {
  const isEditing = !!issue;

  // Form state
  const [title, setTitle] = React.useState(issue?.name ?? '');
  const [description, setDescription] = React.useState(issue?.description ?? '');
  const [state, setState] = React.useState<IssueState>(
    issue?.state ? stateNameToKey(issue.state.name) : defaultState
  );
  const [priority, setPriority] = React.useState<IssuePriority>(issue?.priority ?? 'none');
  // Type selector to be added in future iteration
  const [type, _setType] = React.useState<IssueType>(issue?.type ?? 'task');
  const [selectedLabels, setSelectedLabels] = React.useState<LabelBrief[]>(issue?.labels ?? []);
  const [assignee, setAssignee] = React.useState<UserBrief | null>(issue?.assignee ?? null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [createdIssue, setCreatedIssue] = React.useState<Issue | null>(null);
  const [dismissedDuplicates, setDismissedDuplicates] = React.useState(false);

  // Debounce timer for AI suggestions
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  // Reset form when issue changes
  React.useEffect(() => {
    if (open) {
      setTitle(issue?.name ?? '');
      setDescription(issue?.description ?? '');
      setState(issue?.state ? stateNameToKey(issue.state.name) : defaultState);
      setPriority(issue?.priority ?? 'none');
      _setType(issue?.type ?? 'task');
      setSelectedLabels(issue?.labels ?? []);
      setAssignee(issue?.assignee ?? null);
      setCreatedIssue(null);
      setDismissedDuplicates(false);
    }
  }, [open, issue, defaultState]);

  // Request AI enhancement when title changes (debounced)
  React.useEffect(() => {
    if (!open || !onRequestEnhancement || isEditing) return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (title.length >= 10) {
      debounceTimerRef.current = setTimeout(() => {
        onRequestEnhancement(title, description || null);
        onCheckDuplicates?.(title, description || null);
      }, 1000);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [title, description, open, isEditing, onRequestEnhancement, onCheckDuplicates]);

  // Request assignee recommendations when labels change
  React.useEffect(() => {
    if (!open || !onRequestAssigneeRecommendations) return;

    const labelNames = selectedLabels.map((l) => l.name);
    if (labelNames.length > 0 || title.length >= 10) {
      onRequestAssigneeRecommendations(labelNames);
    }
  }, [selectedLabels, title, open, onRequestAssigneeRecommendations]);

  const handleSave = async () => {
    if (!title.trim()) return;

    setIsSaving(true);
    try {
      const data: CreateIssueData | UpdateIssueData = {
        name: title.trim(),
        description: description.trim() || undefined,
        stateId: state,
        priority,
        type,
        labelIds: selectedLabels.map((l) => l.id),
        assigneeId: assignee?.id,
        projectId,
      };

      const result = await onSave(data);
      if (result) {
        if (isEditing) {
          onOpenChange(false);
        } else {
          setCreatedIssue(result);
        }
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleAcceptEnhancedTitle = () => {
    if (enhancementSuggestion?.enhancedTitle) {
      setTitle(enhancementSuggestion.enhancedTitle);
      onRecordDecision?.('title', true);
    }
  };

  const handleAcceptEnhancedDescription = () => {
    if (enhancementSuggestion?.enhancedDescription) {
      setDescription(enhancementSuggestion.enhancedDescription);
      onRecordDecision?.('description', true);
    }
  };

  const handlePriorityChange = (newPriority: IssuePriority) => {
    setPriority(newPriority);
  };

  const handleOpenCreatedIssue = () => {
    if (createdIssue && onOpenIssue) {
      onOpenIssue(createdIssue);
    }
    onOpenChange(false);
  };

  const handleCreateAnother = () => {
    setCreatedIssue(null);
    setTitle('');
    setDescription('');
    setState(defaultState);
    setPriority('none');
    _setType('task');
    setSelectedLabels([]);
    setAssignee(null);
    setDismissedDuplicates(false);
  };

  const showDuplicateWarning =
    !dismissedDuplicates && duplicateResult && duplicateResult.candidates.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Issue' : 'Create Issue'}</DialogTitle>
          <DialogDescription>
            {isEditing ? `Editing ${issue.identifier}` : 'Create a new issue in this project'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Title */}
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">
              Title <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Issue title..."
                className="pr-10"
              />
              {isLoadingEnhancement && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="size-4 animate-spin text-ai" />
                </div>
              )}
            </div>

            {/* Enhanced title suggestion */}
            {enhancementSuggestion?.titleEnhanced &&
              enhancementSuggestion.enhancedTitle !== title && (
                <div className="flex items-start gap-2 rounded-md border border-ai/20 bg-ai/5 p-2">
                  <Sparkles className="size-4 shrink-0 mt-0.5 text-ai" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{enhancementSuggestion.enhancedTitle}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleAcceptEnhancedTitle}
                    className="shrink-0 text-ai hover:bg-ai/10"
                  >
                    Apply
                  </Button>
                </div>
              )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the issue..."
              rows={4}
              className={cn(
                'flex w-full rounded-md border border-input bg-background px-3 py-2',
                'text-sm ring-offset-background placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'resize-none'
              )}
            />

            {/* Enhanced description suggestion */}
            {enhancementSuggestion?.descriptionExpanded &&
              enhancementSuggestion.enhancedDescription &&
              enhancementSuggestion.enhancedDescription !== description && (
                <div className="flex items-start gap-2 rounded-md border border-ai/20 bg-ai/5 p-2">
                  <Sparkles className="size-4 shrink-0 mt-0.5 text-ai" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm line-clamp-3">
                      {enhancementSuggestion.enhancedDescription}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleAcceptEnhancedDescription}
                    className="shrink-0 text-ai hover:bg-ai/10"
                  >
                    Apply
                  </Button>
                </div>
              )}
          </div>

          {/* Duplicate warning */}
          {showDuplicateWarning && (
            <DuplicateWarning
              candidates={duplicateResult.candidates}
              hasLikelyDuplicate={duplicateResult.hasLikelyDuplicate}
              highestSimilarity={duplicateResult.highestSimilarity}
              onViewDuplicate={(c) => onViewDuplicate?.(c.issueId)}
              onDismiss={() => setDismissedDuplicates(true)}
              onProceed={() => setDismissedDuplicates(true)}
            />
          )}

          <Separator />

          {/* State and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">State</label>
              <IssueStateSelect value={state} onChange={setState} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Priority</label>
              <IssuePrioritySelect
                value={priority}
                onChange={handlePriorityChange}
                suggestion={enhancementSuggestion?.suggestedPriority}
                onSuggestionAccept={() => onRecordDecision?.('priority', true)}
                onSuggestionReject={() => onRecordDecision?.('priority', false)}
              />
            </div>
          </div>

          {/* Labels */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Labels</label>
            <LabelSelector
              selectedLabels={selectedLabels}
              availableLabels={availableLabels}
              suggestions={enhancementSuggestion?.suggestedLabels}
              onChange={setSelectedLabels}
              onCreateLabel={onCreateLabel}
              onSuggestionAccept={() => onRecordDecision?.('label', true)}
              onSuggestionReject={() => onRecordDecision?.('label', false)}
            />
          </div>

          {/* Assignee */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Assignee</label>
            <AssigneeSelector
              value={assignee}
              members={teamMembers}
              recommendations={assigneeRecommendations}
              onChange={setAssignee}
              onRecommendationAccept={() => onRecordDecision?.('assignee', true)}
              onRecommendationReject={() => onRecordDecision?.('assignee', false)}
            />
          </div>
        </div>

        <DialogFooter className="mt-6">
          {createdIssue ? (
            <>
              <div className="flex items-center gap-2 mr-auto text-sm text-primary">
                <CheckCircle2 className="size-4" />
                <span>Issue created: {createdIssue.identifier ?? createdIssue.name}</span>
              </div>
              <Button variant="outline" onClick={handleCreateAnother}>
                Create Another
              </Button>
              <Button onClick={handleOpenCreatedIssue}>
                <ExternalLink className="mr-2 size-4" />
                Open Issue
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={!title.trim() || isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Saving...
                  </>
                ) : isEditing ? (
                  'Save Changes'
                ) : (
                  'Create Issue'
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

export default IssueModal;
