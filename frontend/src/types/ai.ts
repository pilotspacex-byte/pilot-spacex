import type { IssuePriority } from './workspace';

// =============================================================================
// AI Context Types (matches backend AIContextResponse — BaseModel → snake_case)
// =============================================================================

export interface AIContextContent {
  summary: string;
  analysis: string;
  complexity: string;
  estimated_effort: string;
  key_considerations: string[];
  suggested_approach: string;
  potential_blockers: string[];
}

export interface AIRelatedItem {
  id: string;
  type: string;
  title: string;
  relevance_score: number;
  excerpt: string;
  identifier?: string | null;
  state?: string | null;
}

export interface AICodeReference {
  file_path: string;
  line_start?: number | null;
  line_end?: number | null;
  description: string;
  relevance: string;
  source?: string | null;
  source_id?: string | null;
}

export interface AITaskItem {
  id: string;
  description: string;
  completed: boolean;
  dependencies: string[];
  estimated_effort: string;
  order: number;
}

export interface AIContext {
  id: string;
  issue_id: string;
  workspace_id: string;
  content: AIContextContent;
  claude_code_prompt?: string | null;
  related_issues: AIRelatedItem[];
  related_notes: AIRelatedItem[];
  related_pages: AIRelatedItem[];
  code_references: AICodeReference[];
  tasks_checklist: AITaskItem[];
  task_count: number;
  completed_task_count: number;
  conversation_count: number;
  has_conversation: boolean;
  has_plan: boolean;
  generated_at: string;
  last_refined_at?: string | null;
  version: number;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Code Reference (matches backend CodeReferenceSchema — BaseSchema → camelCase)
// Used in Task create/update requests.
// =============================================================================

export interface CodeReference {
  file: string;
  lines?: string | null;
  description?: string | null;
  badge?: string | null;
}

export interface SuggestedTask {
  title: string;
  description: string;
  estimatedHours?: number;
  priority: IssuePriority;
}

// Task Management (013)
export type TaskStatus = 'todo' | 'in_progress' | 'done';

export interface AcceptanceCriterion {
  text: string;
  done: boolean;
}

export interface Task {
  id: string;
  issueId: string;
  workspaceId: string;
  title: string;
  description?: string;
  acceptanceCriteria: AcceptanceCriterion[];
  status: TaskStatus;
  sortOrder: number;
  estimatedHours?: number;
  codeReferences: CodeReference[];
  aiPrompt?: string;
  aiGenerated: boolean;
  dependencyIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  acceptanceCriteria?: AcceptanceCriterion[];
  estimatedHours?: number;
  codeReferences?: CodeReference[];
  aiPrompt?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  acceptanceCriteria?: AcceptanceCriterion[];
  status?: TaskStatus;
  estimatedHours?: number;
  codeReferences?: CodeReference[];
  aiPrompt?: string;
  sortOrder?: number;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  completed: number;
  completionPercent: number;
}

/**
 * Subtask from AI decomposition (backend SubtaskSchema, BaseSchema → camelCase).
 */
export interface SubtaskSchema {
  order: number;
  name: string;
  description: string | null;
  confidence: string; // 'RECOMMENDED' | 'DEFAULT' | 'ALTERNATIVE'
  estimatedDays: number | null;
  labels: string[] | null;
  dependencies: number[] | null;
  acceptanceCriteria: Record<string, unknown>[] | null;
  codeReferences: CodeReference[] | null;
  aiPrompt: string | null;
}

/**
 * Response from AI decomposition endpoint (backend DecomposeResponse, BaseSchema → camelCase).
 * Note: has subtasks[], not tasks[] — distinct from TaskListResponse.
 */
export interface DecomposeResponse {
  subtasks: SubtaskSchema[];
  summary: string | null;
  totalEstimatedDays: number | null;
  criticalPath: number[] | null;
  parallelOpportunities: string[] | null;
}

/**
 * Context export response from backend ContextExportResponse (BaseSchema → camelCase).
 * Backend fields: content, format, generated_at (→ generatedAt), stats.
 * Valid formats: 'markdown' | 'claude_code' | 'task_list'.
 */
export interface ContextExportResponse {
  content: string;
  format: string;
  generatedAt: string;
  stats: Record<string, number>;
}

// Ghost Text Types
export interface GhostTextSuggestion {
  text: string;
  cursorPosition: number;
  confidence: number;
}
