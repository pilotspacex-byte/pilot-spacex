'use client';

/**
 * useMonacoSlashCmd — Monaco CompletionItemProvider for slash commands and @ mentions.
 *
 * Registers TWO CompletionItemProviders for 'markdown' language:
 * 1. Slash commands (trigger: '/') — headings, lists, code blocks, PM blocks, etc.
 * 2. Mentions (trigger: '@') — workspace members via fetchMembers callback
 */
import { useEffect, useRef } from 'react';
import type * as monacoNs from 'monaco-editor';
import { getRegisteredSlashCommands } from '../../plugins/registry/PluginRegistry';

export type MemberFetcher = () => Promise<{ id: string; name: string; email: string }[]>;

/** Slash command definition for Monaco completions */
interface SlashCommandDef {
  label: string;
  description: string;
  insertText: string;
}

/**
 * Get all slash command definitions for Monaco.
 * These map to markdown insert text (not TipTap editor commands).
 */
function getSlashCommands(): SlashCommandDef[] {
  return [
    // Formatting
    { label: 'Heading 1', description: 'Large section heading', insertText: '# ' },
    { label: 'Heading 2', description: 'Medium section heading', insertText: '## ' },
    { label: 'Heading 3', description: 'Small section heading', insertText: '### ' },

    // Blocks
    { label: 'Bullet List', description: 'Create a simple bullet list', insertText: '- ' },
    {
      label: 'Numbered List',
      description: 'Create a numbered list',
      insertText: '1. ',
    },
    {
      label: 'Todo List',
      description: 'Track tasks with a todo list',
      insertText: '- [ ] ',
    },
    { label: 'Quote', description: 'Capture a quote', insertText: '> ' },
    {
      label: 'Code Block',
      description: 'Capture a code snippet',
      insertText: '```\n\n```',
    },
    { label: 'Divider', description: 'Visually divide blocks', insertText: '---\n' },
    {
      label: 'Diagram',
      description: 'Insert a Mermaid diagram',
      insertText: '```mermaid\nflowchart TD\n  A[Start] --> B[End]\n```',
    },

    // PM blocks
    {
      label: 'Decision Record',
      description: 'Insert a decision record with options and pros/cons',
      insertText: '```pm:decision\n{\n  "title": "",\n  "status": "draft"\n}\n```',
    },
    {
      label: 'RACI Matrix',
      description: 'Insert a RACI responsibility matrix',
      insertText:
        '```pm:raci\n{\n  "title": "RACI Matrix",\n  "stakeholders": [],\n  "deliverables": []\n}\n```',
    },
    {
      label: 'Risk Register',
      description: 'Insert a risk register with scoring',
      insertText: '```pm:risk\n{\n  "title": "Risk Register",\n  "risks": []\n}\n```',
    },
    {
      label: 'Dependency Map',
      description: 'Insert a dependency map',
      insertText: '```pm:dependency\n{\n  "title": "Dependencies",\n  "items": []\n}\n```',
    },
    {
      label: 'Timeline',
      description: 'Insert a project timeline with milestones',
      insertText: '```pm:timeline\n{\n  "title": "Project Timeline",\n  "milestones": []\n}\n```',
    },
    {
      label: 'Sprint Board',
      description: 'Insert a sprint board',
      insertText: '```pm:sprint-board\n{\n  "title": "Sprint Board",\n  "columns": []\n}\n```',
    },
    {
      label: 'KPI Dashboard',
      description: 'Insert a KPI dashboard with metrics',
      insertText: '```pm:dashboard\n{\n  "title": "KPI Dashboard",\n  "widgets": []\n}\n```',
    },
    {
      label: 'Form',
      description: 'Insert an interactive form with validation',
      insertText: '```pm:form\n{\n  "title": "Untitled Form",\n  "fields": []\n}\n```',
    },
    {
      label: 'Release Notes',
      description: 'Insert release notes',
      insertText:
        '```pm:release-notes\n{\n  "title": "Release Notes",\n  "version": "",\n  "sections": []\n}\n```',
    },
    {
      label: 'Capacity Plan',
      description: 'Insert a capacity plan',
      insertText: '```pm:capacity-plan\n{\n  "title": "Capacity Plan",\n  "teams": []\n}\n```',
    },
  ];
}

/**
 * Hook that registers Monaco CompletionItemProviders for slash commands and mentions.
 *
 * @param monacoInstance - The monaco namespace
 * @param editor - The Monaco editor instance
 * @param fetchMembers - Optional async function to fetch workspace members for @ mentions
 */
export function useMonacoSlashCmd(
  monacoInstance: typeof monacoNs | null,
  editor: monacoNs.editor.IStandaloneCodeEditor | null,
  fetchMembers?: MemberFetcher
): void {
  const slashDisposableRef = useRef<monacoNs.IDisposable | null>(null);
  const mentionDisposableRef = useRef<monacoNs.IDisposable | null>(null);
  const fetchMembersRef = useRef(fetchMembers);

  // Keep ref current via effect (React 19 rule: no ref writes during render)
  useEffect(() => {
    fetchMembersRef.current = fetchMembers;
  }, [fetchMembers]);

  useEffect(() => {
    if (!monacoInstance || !editor) return;

    const commands = getSlashCommands();

    // 1. Slash command provider (trigger: '/')
    slashDisposableRef.current = monacoInstance.languages.registerCompletionItemProvider(
      'markdown',
      {
        triggerCharacters: ['/'],

        provideCompletionItems: (model, position) => {
          const lineContent = model.getLineContent(position.lineNumber);

          // Find the position of '/' in the current line before cursor
          const textBeforeCursor = lineContent.substring(0, position.column - 1);
          const slashIndex = textBeforeCursor.lastIndexOf('/');

          const range = new monacoInstance.Range(
            position.lineNumber,
            slashIndex + 1, // column of '/' (1-based)
            position.lineNumber,
            position.column
          );

          const builtInSuggestions: monacoNs.languages.CompletionItem[] = commands.map(
            (cmd, index) => ({
              label: cmd.label,
              kind: monacoInstance.languages.CompletionItemKind.Function,
              insertText: cmd.insertText,
              documentation: cmd.description,
              range,
              sortText: index.toString().padStart(3, '0'),
            })
          );

          // Append plugin-registered slash commands after built-in ones
          const pluginCmds = getRegisteredSlashCommands();
          const pluginSuggestions: monacoNs.languages.CompletionItem[] = pluginCmds.map(
            (cmd, index) => ({
              label: cmd.label,
              kind: monacoInstance.languages.CompletionItemKind.Function,
              insertText: `\`\`\`pm:${cmd.trigger}\n{\n  \n}\n\`\`\``,
              documentation: cmd.description,
              detail: `Plugin: ${cmd.pluginName}`,
              range,
              sortText: (commands.length + index).toString().padStart(3, '0'),
            })
          );

          return { suggestions: [...builtInSuggestions, ...pluginSuggestions] };
        },
      }
    );

    // 2. Mention provider (trigger: '@')
    mentionDisposableRef.current = monacoInstance.languages.registerCompletionItemProvider(
      'markdown',
      {
        triggerCharacters: ['@'],

        provideCompletionItems: async (model, position) => {
          const lineContent = model.getLineContent(position.lineNumber);
          const textBeforeCursor = lineContent.substring(0, position.column - 1);
          const atIndex = textBeforeCursor.lastIndexOf('@');

          const range = new monacoInstance.Range(
            position.lineNumber,
            atIndex + 1, // column of '@' (1-based)
            position.lineNumber,
            position.column
          );

          if (!fetchMembersRef.current) {
            return { suggestions: [] };
          }

          let members: { id: string; name: string; email: string }[];
          try {
            members = await fetchMembersRef.current();
          } catch {
            return { suggestions: [] };
          }

          const suggestions: monacoNs.languages.CompletionItem[] = members.map((member, index) => ({
            label: member.name,
            kind: monacoInstance.languages.CompletionItemKind.User,
            insertText: `@${member.name}`,
            detail: member.email,
            range,
            sortText: index.toString().padStart(3, '0'),
          }));

          return { suggestions };
        },
      }
    );

    return () => {
      slashDisposableRef.current?.dispose();
      slashDisposableRef.current = null;
      mentionDisposableRef.current?.dispose();
      mentionDisposableRef.current = null;
    };
  }, [monacoInstance, editor]);
}
