# Data Model: AI Context Tab

**Branch**: `005-conversation-fix` | **Date**: 2026-02-02

## TypeScript Interfaces

### ContextSummary

```typescript
export interface ContextSummary {
  /** Issue identifier (e.g., "PS-201") */
  issueIdentifier: string;
  /** Issue title */
  title: string;
  /** AI-generated summary paragraph */
  summaryText: string;
  /** Counts for stats display */
  stats: ContextStats;
}

export interface ContextStats {
  relatedCount: number;
  docsCount: number;
  filesCount: number;
  tasksCount: number;
}
```

### ContextRelatedIssue

```typescript
export type RelationType = 'blocks' | 'relates' | 'blocked_by';

export interface ContextRelatedIssue {
  /** Relationship type to current issue */
  relationType: RelationType;
  /** UUID of related issue */
  issueId: string;
  /** Human-readable identifier (e.g., "PS-202") */
  identifier: string;
  /** Issue title */
  title: string;
  /** AI-generated summary of relevance */
  summary: string;
  /** Current status display text (e.g., "In Progress") */
  status: string;
  /** State group for color coding (backlog/unstarted/started/completed/cancelled) */
  stateGroup: string;
}
```

### ContextRelatedDoc

```typescript
export type DocType = 'note' | 'adr' | 'spec';

export interface ContextRelatedDoc {
  /** Document type */
  docType: DocType;
  /** Document title */
  title: string;
  /** AI-generated summary of relevance */
  summary: string;
  /** Optional URL to navigate to document */
  url?: string;
}
```

### ContextTask

```typescript
export interface ContextTask {
  /** Task number (1-based) */
  id: number;
  /** Task title */
  title: string;
  /** Estimated effort (e.g., "~2h") */
  estimate: string;
  /** IDs of tasks this depends on */
  dependencies: number[];
  /** Whether task is completed (session-local, not persisted) */
  completed: boolean;
}
```

### ContextPrompt

```typescript
export interface ContextPrompt {
  /** ID of the task this prompt belongs to */
  taskId: number;
  /** Prompt title (e.g., "Task 1: Create Magic Link Service") */
  title: string;
  /** Full prompt content for Claude Code */
  content: string;
}
```

### AIContextResult (Extended)

```typescript
export interface AIContextResult {
  // --- New structured fields (Phase 1) ---
  summary: ContextSummary | null;
  relatedIssues: ContextRelatedIssue[];
  relatedDocs: ContextRelatedDoc[];
  tasks: ContextTask[];
  prompts: ContextPrompt[];

  // --- Legacy fields (backward compat) ---
  phases: AIContextPhase[];
  claudeCodePrompt: string;
  relatedDocs_legacy: string[];
  relatedCode: string[];
  similarIssues: string[];
}
```

### Section Error State

```typescript
export type ContextSection =
  | 'summary'
  | 'related_issues'
  | 'related_docs'
  | 'tasks'
  | 'prompts';

// Stored in AIContextStore as: sectionErrors: Map<ContextSection, string>
```

## State Transitions

```
[No Context] --generateContext()--> [Loading]
[Loading] --SSE events arrive--> [Partial Results] (sections render independently)
[Loading] --context_complete--> [Complete Results]
[Loading] --all events error--> [Error]
[Complete Results] --Regenerate--> [Loading] (cache cleared)
[Error] --Retry--> [Loading]
```

## Validation Rules

- `ContextSummary.issueIdentifier`: Non-empty string, matches `[A-Z]+-\d+` pattern
- `ContextSummary.stats.*`: Non-negative integers
- `ContextRelatedIssue.relationType`: Must be one of `blocks`, `relates`, `blocked_by`
- `ContextRelatedDoc.docType`: Must be one of `note`, `adr`, `spec`
- `ContextTask.id`: Positive integer, unique within array
- `ContextTask.dependencies`: Array of valid task IDs (references within same array)
- `ContextPrompt.taskId`: Must reference existing task ID
