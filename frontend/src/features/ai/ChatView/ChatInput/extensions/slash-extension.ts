/**
 * Slash-command registry + pure helpers for the chat composer slash menu.
 *
 * Phase 87 Plan 02 (Wave 2). The 11-command registry powers SlashMenu.tsx
 * and the dispatch in ChatInput.tsx.
 *
 * IMPORTANT — slash trigger lives in ChatInput's plain contenteditable handler,
 * NOT in a TipTap Suggestion plugin. ChatInput is a hand-rolled `<div
 * contentEditable>` (see ChatInput.tsx `handleInput`). The plan originally
 * specified `@tiptap/suggestion` + `startOfLine: true`; that was incorrect for
 * this composer and is documented in 87-02-SUMMARY.md. The behavior the plan
 * required ("`/` at start of empty paragraph triggers; mid-word does not") is
 * encoded in `shouldTrigger` below and enforced by ChatInput's text-before-cursor
 * detection.
 *
 * @module features/ai/ChatView/ChatInput/extensions/slash-extension
 */

import type { ChatMode } from '../types';

export type SlashCommandKind = 'route' | 'invoke' | 'picker';

/** Minimal router shape this module needs — matches Next.js `AppRouterInstance.push`. */
export interface SlashRouter {
  push: (path: string) => void;
}

/** Context handed to invoke-kind commands when dispatched from ChatInput. */
export interface SlashInvokeContext {
  workspaceSlug: string;
  router: SlashRouter;
  submitMessage: (payload: {
    content: string;
    mode?: ChatMode;
    command?: string;
  }) => Promise<void> | void;
  emitSystemMessage: (text: string) => void;
}

export interface SlashCommand {
  /** Stable id used for `data-slash-row="..."` and dispatch routing. */
  id: string;
  /** Display keyword including the leading slash, e.g. `/topic`. */
  keyword: string;
  /** Human-readable description shown next to the keyword. */
  description: string;
  /** Lucide icon name; resolved by SlashMenu via the icon lookup map. */
  iconName: string;
  /** Brand hex (`#29a386`) or the literal `"muted"` for `text-muted-foreground`. */
  iconColor: string;
  kind: SlashCommandKind;
  /** Builds the navigation target for `route` and `picker` kinds. */
  routeTemplate?: (workspaceSlug: string) => string;
  /** Invoked for `invoke` kind (dispatches an inline chat submission). */
  invoke?: (ctx: SlashInvokeContext) => Promise<void> | void;
  /** When true the route may 404 today; ChatInput emits a "Coming soon" system msg. */
  stubTolerant?: boolean;
}

/**
 * The 11 slash commands rendered by SlashMenu, in the documented order.
 *
 * Plan 89 may extend this array additively for new picker/invoke commands.
 */
export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: 'topic',
    keyword: '/topic',
    description: 'Open or create a topic',
    iconName: 'Hash',
    iconColor: '#29a386',
    kind: 'picker',
    routeTemplate: (ws) => `/${ws}/topics/new`,
  },
  {
    id: 'task',
    keyword: '/task',
    description: 'Create a new task',
    iconName: 'CheckSquare',
    iconColor: '#3b82f6',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/tasks/new`,
  },
  {
    id: 'spec',
    keyword: '/spec',
    description: 'Open spec composer',
    iconName: 'FileText',
    iconColor: '#8b5cf6',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/specs/new`,
    stubTolerant: true,
  },
  {
    id: 'decision',
    keyword: '/decision',
    description: 'Record a decision',
    iconName: 'GitCommit',
    iconColor: '#d9853f',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/decisions/new`,
    stubTolerant: true,
  },
  // Phase 91 Plan 05 — /skills (plural) opens the gallery directly.
  // Inserted BEFORE /skill so typing "/sk" surfaces both options with
  // /skills first.
  {
    id: 'skills',
    keyword: '/skills',
    description: 'Browse all skills',
    iconName: 'BookOpen',
    iconColor: '#29a386',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/skills`,
  },
  // Phase 92 Plan 03 — /skills-graph opens the gallery in graph mode.
  // Single-token entry locked per UI-SPEC OQ4: multi-token `/skills graph`
  // is impossible because shouldTrigger rejects whitespace (slash-extension
  // .ts:213). Inserted BETWEEN /skills and /skill so typing "/sk" surfaces
  // the three options in order: /skills, /skills-graph, /skill.
  {
    id: 'skills-graph',
    keyword: '/skills-graph',
    description: 'Open the skill dependency graph',
    iconName: 'Network',
    iconColor: '#7c5cff',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/skills?view=graph`,
  },
  // Phase 91 Plan 05 — /skill <name> repurposed: was "Run a skill" (chat
  // submission via SkillMenu text-insert); now opens the detail page on
  // pick. The bare-keyword Enter still routes to the gallery via
  // routeTemplate. stubTolerant removed — the route is no longer a stub.
  {
    id: 'skill',
    keyword: '/skill',
    description: 'Open a skill by name',
    iconName: 'Wand2',
    iconColor: '#29a386',
    kind: 'picker',
    routeTemplate: (ws) => `/${ws}/skills`,
  },
  {
    id: 'members',
    keyword: '/members',
    description: 'Browse members',
    iconName: 'Users',
    iconColor: 'muted',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/members`,
  },
  {
    id: 'settings',
    keyword: '/settings',
    description: 'Open workspace settings',
    iconName: 'Settings',
    iconColor: 'muted',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/settings`,
  },
  {
    id: 'integrations',
    keyword: '/integrations',
    description: 'Manage integrations',
    iconName: 'Plug',
    iconColor: 'muted',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/settings/integrations`,
    stubTolerant: true,
  },
  {
    id: 'kg',
    keyword: '/kg',
    description: 'Open knowledge graph',
    iconName: 'Network',
    iconColor: '#8b5cf6',
    kind: 'route',
    routeTemplate: (ws) => `/${ws}/knowledge`,
    stubTolerant: true,
  },
  {
    id: 'standup',
    keyword: '/standup',
    description: 'Run standup skill in chat',
    iconName: 'CalendarDays',
    iconColor: 'muted',
    kind: 'invoke',
    invoke: async (ctx) => {
      await ctx.submitMessage({
        content: '/standup',
        mode: 'research',
        command: 'standup',
      });
    },
  },
  {
    id: 'digest',
    keyword: '/digest',
    description: 'Run digest skill in chat',
    iconName: 'Newspaper',
    iconColor: 'muted',
    kind: 'invoke',
    invoke: async (ctx) => {
      await ctx.submitMessage({
        content: '/digest',
        mode: 'research',
        command: 'digest',
      });
    },
  },
];

/**
 * Returns true when the slash menu should be open given the text-before-cursor.
 *
 * Rule (per UI-SPEC §3): trigger only when the entire text-before-cursor begins
 * with `/` and contains no whitespace. This means `/`, `/t`, `/topic` all
 * trigger; `http://`, `hello /`, ` /task` do not. The empty string never
 * triggers.
 *
 * The runtime check in ChatInput.handleInput uses the same rule against the
 * full text-before-cursor extracted via `getTextBeforeCursor`.
 */
export function shouldTrigger(args: { textBeforeCursor: string }): boolean {
  const t = args.textBeforeCursor;
  if (t.length === 0) return false;
  if (!t.startsWith('/')) return false;
  if (/\s/.test(t)) return false;
  return true;
}

/**
 * Substring filter (case-insensitive) over keyword + description. Returns the
 * full registry in declaration order when the query is empty.
 */
export function filterCommands(
  query: string,
  commands: SlashCommand[] = SLASH_COMMANDS,
): SlashCommand[] {
  const q = query.trim().toLowerCase();
  if (!q) return commands;
  return commands.filter(
    (c) => c.keyword.toLowerCase().includes(q) || c.description.toLowerCase().includes(q),
  );
}
