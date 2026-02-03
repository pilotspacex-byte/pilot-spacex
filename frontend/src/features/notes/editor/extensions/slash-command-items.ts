/**
 * Slash command definitions and filtering logic.
 *
 * Extracted from SlashCommandExtension to keep files under 700 lines.
 */
import type { Editor } from '@tiptap/core';

/**
 * Slash command definition
 */
export interface SlashCommand {
  /** Command name (e.g., 'heading') */
  name: string;
  /** Display label */
  label: string;
  /** Description for menu */
  description: string;
  /** Icon name (Lucide icon) */
  icon: string;
  /** Command group */
  group: 'formatting' | 'blocks' | 'ai';
  /** Keyboard shortcut hint */
  shortcut?: string;
  /** Execute the command */
  execute: (editor: Editor) => void;
  /** Search keywords */
  keywords?: string[];
}

/**
 * Default slash commands
 */
export function getDefaultCommands(
  onAICommand?: (command: string, editor: Editor) => Promise<void>
): SlashCommand[] {
  return [
    // Formatting commands
    {
      name: 'heading1',
      label: 'Heading 1',
      description: 'Large section heading',
      icon: 'Heading1',
      group: 'formatting',
      shortcut: '# ',
      keywords: ['h1', 'title', 'large'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      name: 'heading2',
      label: 'Heading 2',
      description: 'Medium section heading',
      icon: 'Heading2',
      group: 'formatting',
      shortcut: '## ',
      keywords: ['h2', 'subtitle', 'medium'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      name: 'heading3',
      label: 'Heading 3',
      description: 'Small section heading',
      icon: 'Heading3',
      group: 'formatting',
      shortcut: '### ',
      keywords: ['h3', 'small'],
      execute: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
    },

    // Block commands
    {
      name: 'bullet',
      label: 'Bullet List',
      description: 'Create a simple bullet list',
      icon: 'List',
      group: 'blocks',
      shortcut: '- ',
      keywords: ['ul', 'unordered', 'list'],
      execute: (editor) => editor.chain().focus().toggleBulletList().run(),
    },
    {
      name: 'numbered',
      label: 'Numbered List',
      description: 'Create a numbered list',
      icon: 'ListOrdered',
      group: 'blocks',
      shortcut: '1. ',
      keywords: ['ol', 'ordered', 'number'],
      execute: (editor) => editor.chain().focus().toggleOrderedList().run(),
    },
    {
      name: 'todo',
      label: 'Todo List',
      description: 'Track tasks with a todo list',
      icon: 'CheckSquare',
      group: 'blocks',
      keywords: ['checkbox', 'task', 'check'],
      execute: (editor) => editor.chain().focus().toggleTaskList().run(),
    },
    {
      name: 'quote',
      label: 'Quote',
      description: 'Capture a quote',
      icon: 'Quote',
      group: 'blocks',
      shortcut: '> ',
      keywords: ['blockquote', 'citation'],
      execute: (editor) => editor.chain().focus().toggleBlockquote().run(),
    },
    {
      name: 'code',
      label: 'Code Block',
      description: 'Capture a code snippet',
      icon: 'Code',
      group: 'blocks',
      shortcut: '```',
      keywords: ['codeblock', 'snippet', 'programming'],
      execute: (editor) => editor.chain().focus().toggleCodeBlock().run(),
    },
    {
      name: 'divider',
      label: 'Divider',
      description: 'Visually divide blocks',
      icon: 'Minus',
      group: 'blocks',
      shortcut: '---',
      keywords: ['hr', 'horizontal', 'line', 'separator'],
      execute: (editor) => editor.chain().focus().setHorizontalRule().run(),
    },

    // AI commands
    {
      name: 'ai-improve',
      label: 'AI: Improve Writing',
      description: 'Improve selected text with AI',
      icon: 'Sparkles',
      group: 'ai',
      keywords: ['enhance', 'rewrite', 'polish'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('improve', editor);
        }
      },
    },
    {
      name: 'ai-summarize',
      label: 'AI: Summarize',
      description: 'Summarize the document',
      icon: 'FileText',
      group: 'ai',
      keywords: ['summary', 'tldr', 'brief'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('summarize', editor);
        }
      },
    },
    {
      name: 'ai-extract-issues',
      label: 'AI: Extract Issues',
      description: 'Find potential issues to create',
      icon: 'ListTodo',
      group: 'ai',
      keywords: ['issues', 'tasks', 'tickets', 'extract'],
      execute: (editor) => {
        if (onAICommand) {
          onAICommand('extract-issues', editor);
        }
      },
    },
  ];
}

/**
 * Filter commands by query
 */
export function filterCommands(commands: SlashCommand[], query: string): SlashCommand[] {
  if (!query) return commands;

  const lowerQuery = query.toLowerCase();
  return commands.filter((cmd) => {
    const matchesName = cmd.name.toLowerCase().includes(lowerQuery);
    const matchesLabel = cmd.label.toLowerCase().includes(lowerQuery);
    const matchesKeywords = cmd.keywords?.some((k) => k.toLowerCase().includes(lowerQuery));
    return matchesName || matchesLabel || matchesKeywords;
  });
}
