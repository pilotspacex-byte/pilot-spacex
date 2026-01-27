/**
 * Static definitions for skills and agents
 * Following pilotspace-agent-architecture.md v1.5.0
 */

import type { SkillDefinition, AgentDefinition } from './types';

/**
 * Available skills for invocation
 * Phase 2: Skill Migration from remediation plan
 */
export const SKILLS: SkillDefinition[] = [
  {
    name: 'extract-issues',
    description: 'Extract structured issues from note content or selected text',
    category: 'issues',
    icon: 'ListTodo',
    examples: ['Extract issues from this note', 'Find actionable items in the selected text'],
  },
  {
    name: 'enhance-issue',
    description: 'Add labels, priority, and acceptance criteria to an issue',
    category: 'issues',
    icon: 'Sparkles',
    examples: ['Enhance this issue with details', 'Add acceptance criteria'],
  },
  {
    name: 'recommend-assignee',
    description: 'Suggest the best team member to assign based on expertise',
    category: 'issues',
    icon: 'UserCog',
    examples: ['Who should work on this?', 'Recommend an assignee'],
  },
  {
    name: 'find-duplicates',
    description: 'Find duplicate or similar issues using semantic search',
    category: 'issues',
    icon: 'Copy',
    examples: ['Find similar issues', 'Check for duplicates'],
  },
  {
    name: 'decompose-tasks',
    description: 'Break down a complex issue into subtasks with dependencies',
    category: 'planning',
    icon: 'Network',
    examples: ['Break this into subtasks', 'Decompose into implementation steps'],
  },
  {
    name: 'generate-diagram',
    description: 'Generate Mermaid diagrams from descriptions',
    category: 'documentation',
    icon: 'GitBranch',
    examples: ['Create a flowchart', 'Generate architecture diagram'],
  },
  {
    name: 'improve-writing',
    description: 'Improve clarity, grammar, and style of text',
    category: 'writing',
    icon: 'PenTool',
    examples: ['Improve this text', 'Make this clearer'],
  },
  {
    name: 'summarize',
    description: 'Create concise summaries of content',
    category: 'notes',
    icon: 'FileText',
    examples: ['Summarize this note', 'Create a brief summary'],
  },
];

/**
 * Available subagents for invocation
 * Phase 3: Backend Consolidation from remediation plan
 */
export const AGENTS: AgentDefinition[] = [
  {
    name: 'pr-review',
    description: 'Expert code review for quality, security, and best practices',
    icon: 'GitPullRequest',
    capabilities: [
      'Architecture analysis',
      'Code quality checks',
      'Security audit',
      'Performance review',
      'Documentation review',
    ],
  },
  {
    name: 'ai-context',
    description: 'Multi-turn context aggregation for issues',
    icon: 'Brain',
    capabilities: [
      'Related documentation search',
      'Code reference extraction',
      'Task suggestion',
      'Claude Code prompt generation',
    ],
  },
  {
    name: 'doc-generator',
    description: 'Generate technical documentation from code',
    icon: 'BookOpen',
    capabilities: [
      'API documentation',
      'Architecture diagrams',
      'README generation',
      'Technical specifications',
    ],
  },
];

/**
 * Skill categories for grouping in menu
 */
export const SKILL_CATEGORIES = [
  { id: 'writing', label: 'Writing', icon: 'PenTool' },
  { id: 'notes', label: 'Notes', icon: 'FileText' },
  { id: 'issues', label: 'Issues', icon: 'ListTodo' },
  { id: 'code', label: 'Code', icon: 'Code' },
  { id: 'documentation', label: 'Documentation', icon: 'BookOpen' },
  { id: 'planning', label: 'Planning', icon: 'Calendar' },
] as const;
