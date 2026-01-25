/**
 * Issue Create/Edit Modal
 *
 * Modal for creating and editing issues with AI assistance.
 * Follows Web Interface Guidelines:
 * - Proper form validation with inline errors
 * - Focus first input on open
 * - Warn before closing with unsaved changes
 * - AI suggestions clearly labeled
 */

import * as React from 'react';
import {
  IconSparkles,
  IconAlertTriangle,
  IconLoader2,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Button } from '../components/button';
import { Input, FormField } from '../components/input';
import { Badge, AIBadge, LabelBadge } from '../components/badge';
import { UserAvatar } from '../components/avatar';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/dialog';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '../components/select';
import type { IssueState, IssuePriority, IssueLabel, IssueAssignee } from './issue-card';

// =============================================================================
// TYPES
// =============================================================================

export interface DuplicateIssue {
  id: string;
  identifier: string;
  title: string;
  similarity: number;
}

export interface AISuggestion {
  type: 'title' | 'description' | 'labels' | 'priority' | 'assignees';
  value: string | string[] | IssuePriority | IssueAssignee[];
  confidence: number;
  rationale?: string;
}

export interface IssueFormData {
  title: string;
  description: string;
  state: IssueState;
  priority: IssuePriority;
  labels: string[];
  assignees: string[];
  moduleId?: string;
  cycleId?: string;
  dueDate?: Date;
}

export interface IssueCreateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: IssueFormData) => Promise<void>;
  initialData?: Partial<IssueFormData>;
  projectIdentifier: string;
  availableLabels: IssueLabel[];
  availableAssignees: IssueAssignee[];
  isEditing?: boolean;
}

// =============================================================================
// AI SUGGESTION PANEL
// =============================================================================

interface AISuggestionPanelProps {
  suggestions: AISuggestion[];
  onAccept: (suggestion: AISuggestion) => void;
  onReject: (suggestion: AISuggestion) => void;
  isLoading: boolean;
}

function AISuggestionPanel({
  suggestions,
  onAccept,
  onReject,
  isLoading,
}: AISuggestionPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-ai-suggestion/20 bg-ai-suggestion/5 p-3">
        <IconLoader2 className="h-4 w-4 animate-spin text-ai-suggestion" />
        <span className="text-sm text-ai-suggestion">
          Analyzing content for suggestions...
        </span>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-lg border border-ai-suggestion/20 bg-ai-suggestion/5 p-3">
      <div className="flex items-center gap-2">
        <IconSparkles className="h-4 w-4 text-ai-suggestion" />
        <span className="text-sm font-medium text-ai-suggestion">
          AI Suggestions
        </span>
      </div>

      <div className="space-y-2">
        {suggestions.map((suggestion, index) => (
          <div
            key={index}
            className="flex items-start justify-between gap-3 rounded-md bg-background p-2"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {suggestion.type}
                </Badge>
                <AIBadge confidence={suggestion.confidence} />
              </div>
              <p className="mt-1 text-sm">
                {typeof suggestion.value === 'string'
                  ? suggestion.value
                  : Array.isArray(suggestion.value)
                    ? suggestion.value.join(', ')
                    : String(suggestion.value)}
              </p>
              {suggestion.rationale && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {suggestion.rationale}
                </p>
              )}
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onAccept(suggestion)}
                aria-label="Accept suggestion"
              >
                <IconCheck className="h-4 w-4 text-green-600" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onReject(suggestion)}
                aria-label="Reject suggestion"
              >
                <IconX className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// DUPLICATE WARNING
// =============================================================================

interface DuplicateWarningProps {
  duplicates: DuplicateIssue[];
  onViewIssue: (id: string) => void;
  onContinue: () => void;
}

function DuplicateWarning({
  duplicates,
  onViewIssue,
  onContinue,
}: DuplicateWarningProps) {
  if (duplicates.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-yellow-500/20 bg-yellow-50 p-3 dark:bg-yellow-950/20">
      <div className="flex items-start gap-2">
        <IconAlertTriangle className="h-5 w-5 flex-shrink-0 text-yellow-600" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            Potential duplicates found
          </p>
          <ul className="mt-2 space-y-1">
            {duplicates.map((dup) => (
              <li key={dup.id} className="flex items-center gap-2">
                <button
                  onClick={() => onViewIssue(dup.id)}
                  className="text-sm text-yellow-700 underline hover:no-underline dark:text-yellow-300"
                >
                  {dup.identifier}
                </button>
                <span className="truncate text-sm text-yellow-600 dark:text-yellow-400">
                  {dup.title}
                </span>
                <Badge variant="outline" className="ml-auto flex-shrink-0">
                  {Math.round(dup.similarity * 100)}% match
                </Badge>
              </li>
            ))}
          </ul>
          <Button
            variant="ghost"
            size="sm"
            onClick={onContinue}
            className="mt-2 text-yellow-700 hover:text-yellow-800 dark:text-yellow-300"
          >
            Continue anyway
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function IssueCreateModal({
  open,
  onOpenChange,
  onSubmit,
  initialData,
  projectIdentifier,
  availableLabels,
  availableAssignees,
  isEditing = false,
}: IssueCreateModalProps) {
  // Form state
  const [title, setTitle] = React.useState(initialData?.title || '');
  const [description, setDescription] = React.useState(initialData?.description || '');
  const [state, setState] = React.useState<IssueState>(initialData?.state || 'backlog');
  const [priority, setPriority] = React.useState<IssuePriority>(initialData?.priority || 'none');
  const [selectedLabels, setSelectedLabels] = React.useState<string[]>(initialData?.labels || []);
  const [selectedAssignees, setSelectedAssignees] = React.useState<string[]>(initialData?.assignees || []);

  // AI and validation state
  const [suggestions, setSuggestions] = React.useState<AISuggestion[]>([]);
  const [duplicates, setDuplicates] = React.useState<DuplicateIssue[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [isDirty, setIsDirty] = React.useState(false);

  // Track dirty state
  React.useEffect(() => {
    if (title || description || selectedLabels.length > 0) {
      setIsDirty(true);
    }
  }, [title, description, selectedLabels]);

  // Request AI suggestions when title changes (debounced)
  React.useEffect(() => {
    if (title.length < 10) return;

    const timer = setTimeout(() => {
      setIsLoadingSuggestions(true);
      // Simulated API call - replace with actual AI service
      setTimeout(() => {
        setSuggestions([
          {
            type: 'title',
            value: `[${projectIdentifier}] ${title}`,
            confidence: 85,
            rationale: 'Added project prefix for better searchability',
          },
          {
            type: 'labels',
            value: ['bug', 'needs-triage'],
            confidence: 72,
            rationale: 'Based on keywords in title',
          },
        ]);
        setIsLoadingSuggestions(false);
      }, 1500);
    }, 1000);

    return () => clearTimeout(timer);
  }, [title, projectIdentifier]);

  // Handle suggestion accept
  const handleAcceptSuggestion = (suggestion: AISuggestion) => {
    switch (suggestion.type) {
      case 'title':
        setTitle(suggestion.value as string);
        break;
      case 'description':
        setDescription(suggestion.value as string);
        break;
      case 'priority':
        setPriority(suggestion.value as IssuePriority);
        break;
      case 'labels':
        setSelectedLabels(suggestion.value as string[]);
        break;
    }
    setSuggestions((prev) => prev.filter((s) => s !== suggestion));
  };

  // Handle suggestion reject
  const handleRejectSuggestion = (suggestion: AISuggestion) => {
    setSuggestions((prev) => prev.filter((s) => s !== suggestion));
  };

  // Validate form
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    } else if (title.length < 5) {
      newErrors.title = 'Title must be at least 5 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        title,
        description,
        state,
        priority,
        labels: selectedLabels,
        assignees: selectedAssignees,
      });
      onOpenChange(false);
    } catch (error) {
      setErrors({ submit: 'Failed to create issue. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle close with dirty check
  const handleClose = () => {
    if (isDirty) {
      // Per Web Interface Guidelines: warn before navigation with unsaved changes
      if (window.confirm('You have unsaved changes. Discard them?')) {
        onOpenChange(false);
      }
    } else {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Issue' : 'Create Issue'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update the issue details below.'
              : 'Fill in the details to create a new issue. AI will help enhance your input.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <FormField
            id="issue-title"
            label="Title"
            required
            error={errors.title}
          >
            <Input
              placeholder="Brief description of the issue..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              autoComplete="off"
            />
          </FormField>

          {/* AI Suggestions */}
          <AISuggestionPanel
            suggestions={suggestions}
            onAccept={handleAcceptSuggestion}
            onReject={handleRejectSuggestion}
            isLoading={isLoadingSuggestions}
          />

          {/* Duplicate Warning */}
          <DuplicateWarning
            duplicates={duplicates}
            onViewIssue={(id) => console.log('View issue:', id)}
            onContinue={() => setDuplicates([])}
          />

          {/* Description */}
          <FormField
            id="issue-description"
            label="Description"
            description="Provide more details. AI can help expand this."
          >
            <textarea
              id="issue-description"
              className={cn(
                'flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2',
                'text-sm ring-offset-background placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
              placeholder="Describe the issue in detail..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </FormField>

          {/* Metadata row */}
          <div className="grid grid-cols-2 gap-4">
            {/* State */}
            <FormField id="issue-state" label="State">
              <Select value={state} onValueChange={(v) => setState(v as IssueState)}>
                <SelectTrigger id="issue-state">
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="backlog">Backlog</SelectItem>
                  <SelectItem value="todo">Todo</SelectItem>
                  <SelectItem value="in-progress">In Progress</SelectItem>
                  <SelectItem value="in-review">In Review</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </FormField>

            {/* Priority */}
            <FormField id="issue-priority" label="Priority">
              <Select value={priority} onValueChange={(v) => setPriority(v as IssuePriority)}>
                <SelectTrigger id="issue-priority">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="none">No Priority</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
          </div>

          {/* Labels */}
          <FormField id="issue-labels" label="Labels">
            <div className="flex flex-wrap gap-2 rounded-md border border-input bg-background p-2">
              {availableLabels.map((label) => (
                <button
                  key={label.id}
                  type="button"
                  onClick={() => {
                    setSelectedLabels((prev) =>
                      prev.includes(label.id)
                        ? prev.filter((id) => id !== label.id)
                        : [...prev, label.id]
                    );
                  }}
                  className={cn(
                    'rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
                    selectedLabels.includes(label.id)
                      ? 'ring-2 ring-primary ring-offset-1'
                      : 'opacity-60 hover:opacity-100'
                  )}
                  style={{
                    backgroundColor: `${label.color}20`,
                    color: label.color,
                  }}
                >
                  {label.name}
                </button>
              ))}
            </div>
          </FormField>

          {/* Assignees */}
          <FormField id="issue-assignees" label="Assignees">
            <div className="flex flex-wrap gap-2 rounded-md border border-input bg-background p-2">
              {availableAssignees.map((assignee) => (
                <button
                  key={assignee.email}
                  type="button"
                  onClick={() => {
                    const id = assignee.email || assignee.name;
                    setSelectedAssignees((prev) =>
                      prev.includes(id)
                        ? prev.filter((a) => a !== id)
                        : [...prev, id]
                    );
                  }}
                  className={cn(
                    'flex items-center gap-2 rounded-full border px-2 py-1 transition-colors',
                    selectedAssignees.includes(assignee.email || assignee.name)
                      ? 'border-primary bg-primary/10'
                      : 'border-transparent hover:border-border'
                  )}
                >
                  <UserAvatar user={assignee} size="xs" />
                  <span className="text-xs">{assignee.name}</span>
                </button>
              ))}
            </div>
          </FormField>

          {/* Error message */}
          {errors.submit && (
            <p className="text-sm text-destructive" role="alert">
              {errors.submit}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEditing ? 'Save Changes' : 'Create Issue'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
