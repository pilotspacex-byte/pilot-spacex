/**
 * Static definitions for skills and agents
 * Following pilotspace-agent-architecture.md v1.5.0
 */

import type { SkillDefinition, AgentDefinition } from './types';

/**
 * Session-only skills (UI-only, no backend SKILL.md).
 * Always included regardless of API response.
 */
export const SESSION_SKILLS: SkillDefinition[] = [
  {
    name: 'resume',
    description: 'Resume a previous conversation session',
    category: 'session',
    icon: 'History',
    examples: ['Continue our last chat', 'Resume discussion about API design'],
  },
  {
    name: 'new',
    description: 'Start a fresh conversation session',
    category: 'session',
    icon: 'Plus',
    examples: ['Start new chat', 'Fresh conversation'],
  },
];

/**
 * Fallback skills used when the backend API is unavailable.
 * Does NOT include session skills — those are merged separately.
 */
export const FALLBACK_SKILLS: SkillDefinition[] = [
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
  {
    name: 'generate-pm-blocks',
    description:
      'Generate PM blocks (decision, risk, timeline, RACI, form, dashboard) from description',
    category: 'planning',
    icon: 'LayoutDashboard',
    examples: ['Generate PM blocks for sprint planning', 'Create risk register and timeline'],
  },
];

/**
 * Combined skills list for backward compatibility.
 * Prefer using useSkills() hook for dynamic loading.
 */
export const SKILLS: SkillDefinition[] = [...SESSION_SKILLS, ...FALLBACK_SKILLS];

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
  { id: 'session', label: 'Session', icon: 'History' },
  { id: 'writing', label: 'Writing', icon: 'PenTool' },
  { id: 'notes', label: 'Notes', icon: 'FileText' },
  { id: 'issues', label: 'Issues', icon: 'ListTodo' },
  { id: 'code', label: 'Code', icon: 'Code' },
  { id: 'documentation', label: 'Documentation', icon: 'BookOpen' },
  { id: 'planning', label: 'Planning', icon: 'Calendar' },
] as const;

/**
 * Human-readable display names for MCP tool invocations.
 * Shown in the tool execution banner during streaming.
 */
export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  update_note_block: 'Updating Note Block',
  enhance_text: 'Enhancing Text',
  summarize_note: 'Summarizing Note',
  extract_issues: 'Extracting Issues',
  create_issue_from_note: 'Creating Issue',
  link_existing_issues: 'Linking Issues',
  create_pm_block: 'Creating PM Block',
};

/** Tool names that are interaction tools (ask_user) — hidden from ToolCallCard */
const INTERACTION_TOOL_PATTERNS = ['ask_user', 'pilot-interaction__ask_user'];

/** Check if a tool call is an interaction tool (ask_user) that should be hidden. */
export function isInteractionTool(toolName: string): boolean {
  const stripped = toolName.replace(/^(?:functions\.)?mcp__[a-z_-]+__/, '');
  return INTERACTION_TOOL_PATTERNS.some(
    (pattern) => stripped === pattern || toolName.includes(pattern)
  );
}

/**
 * Get a human-readable one-line summary for a tool call.
 * Returns null to fall back to default JSON display.
 */
export function getToolSummary(
  name: string,
  input: Record<string, unknown>,
  output?: unknown
): string | null {
  const stripped = name.replace(/^(?:functions\.)?mcp__[a-z_-]+__/, '');

  switch (stripped) {
    case 'update_note_block':
      return input.block_id
        ? `Updated block ${String(input.block_id).slice(0, 8)}…`
        : 'Updated note block';
    case 'create_issue_from_note':
      return input.title ? `Created issue: ${String(input.title)}` : 'Created issue from note';
    case 'enhance_text':
      return 'Enhanced text content';
    case 'summarize_note':
      return 'Summarized note';
    case 'extract_issues':
      if (output && typeof output === 'object' && 'count' in (output as Record<string, unknown>)) {
        return `Extracted ${(output as Record<string, unknown>).count} issues`;
      }
      return 'Extracted issues';
    case 'link_existing_issues':
      return 'Linked issues';
    case 'create_pm_block':
      return input.block_type ? `Created ${String(input.block_type)} block` : 'Created PM block';
    default:
      return null;
  }
}

/**
 * Get a display-friendly name for a tool.
 * Falls back to title-casing the raw snake_case name.
 *
 * @param rawName - Raw tool name from SSE event (e.g., "update_note_block")
 * @returns Human-readable name (e.g., "Updating Note Block")
 */
export function getToolDisplayName(rawName: string): string {
  return (
    TOOL_DISPLAY_NAMES[rawName] ??
    rawName
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ')
  );
}
