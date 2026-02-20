import type { IssuePriority } from './workspace';

export interface AIContext {
  issueId: string;
  relatedDocs: string[];
  codeReferences: CodeReference[];
  suggestedTasks: SuggestedTask[];
  claudeCodePrompts: string[];
}

export interface CodeReference {
  filePath: string;
  lineStart: number;
  lineEnd: number;
  content: string;
  relevance: number;
}

export interface SuggestedTask {
  title: string;
  description: string;
  estimatedHours?: number;
  priority: IssuePriority;
}

// Task Management (013)
export type TaskStatus = 'todo' | 'in_progress' | 'done';

export interface Task {
  id: string;
  issueId: string;
  workspaceId: string;
  title: string;
  description?: string;
  acceptanceCriteria: string[];
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
  acceptanceCriteria?: string[];
  estimatedHours?: number;
  codeReferences?: CodeReference[];
  aiPrompt?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  acceptanceCriteria?: string[];
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

export interface ContextExportResponse {
  content: string;
  format: 'markdown' | 'claude_code' | 'task_list';
  generatedAt: string;
  stats: {
    tasksCount: number;
    relatedIssuesCount: number;
    relatedDocsCount: number;
  };
}

// Ghost Text Types
export interface GhostTextSuggestion {
  text: string;
  cursorPosition: number;
  confidence: number;
}
