/**
 * Slash command definitions and filtering logic.
 *
 * Extracted from SlashCommandExtension to keep files under 700 lines.
 */
import type { Editor } from '@tiptap/core';
import { toast } from 'sonner';
import { isVideoUrl, extractVimeoId } from './VimeoNode';
import { showVideoUrlPrompt } from './VideoUrlPrompt';

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
  group: 'formatting' | 'blocks' | 'ai' | 'media';
  /** Keyboard shortcut hint */
  shortcut?: string;
  /** Execute the command */
  execute: (editor: Editor) => void;
  /** Search keywords */
  keywords?: string[];
}

/**
 * Open a file picker dialog and call callback with selected File objects.
 * Uses a hidden input element — the only cross-browser way to open file picker
 * without a drag-and-drop zone.
 */
function openFilePicker(accept: string, onFiles: (files: File[]) => void, multiple = false): void {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = accept;
  input.multiple = multiple;
  input.style.display = 'none';
  document.body.appendChild(input);

  input.onchange = () => {
    const files = input.files ? Array.from(input.files) : [];
    if (files.length) onFiles(files);
    if (input.parentNode) document.body.removeChild(input);
  };

  // Remove input if dialog is cancelled (focus returns to window)
  const onFocus = () => {
    setTimeout(() => {
      if (input.parentNode) document.body.removeChild(input);
      window.removeEventListener('focus', onFocus);
    }, 300);
  };
  window.addEventListener('focus', onFocus);

  input.click();
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
      name: 'pullquote',
      label: 'Pull Quote',
      description: 'Editorial-style emphasized quote with visual accent',
      icon: 'Quote',
      group: 'blocks',
      keywords: ['pullquote', 'pull', 'quote', 'editorial', 'emphasis', 'callout', 'highlight'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .toggleBlockquote()
          .updateAttributes('blockquote', { pullQuote: true })
          .run(),
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
      name: 'checklist',
      label: 'Checklist',
      description: 'Insert a smart checklist with progress tracking',
      icon: 'ListChecks',
      group: 'blocks',
      keywords: ['checklist', 'todo', 'tasks', 'sprint', 'done', 'progress'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .toggleTaskList()
          .insertContent([
            {
              type: 'taskItem',
              attrs: { checked: false },
              content: [{ type: 'paragraph', content: [{ type: 'text', text: 'First item' }] }],
            },
            {
              type: 'taskItem',
              attrs: { checked: false },
              content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Second item' }] }],
            },
            {
              type: 'taskItem',
              attrs: { checked: false },
              content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Third item' }] }],
            },
          ])
          .run(),
    },
    {
      name: 'diagram',
      label: 'Diagram',
      description: 'Insert a Mermaid diagram',
      icon: 'GitBranch',
      group: 'blocks',
      keywords: ['mermaid', 'flowchart', 'sequence', 'gantt', 'class', 'er', 'diagram', 'chart'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .setCodeBlock({ language: 'mermaid' })
          .insertContent('flowchart TD\n  A[Start] --> B[End]')
          .run(),
    },
    {
      name: 'decision',
      label: 'Decision Record',
      description: 'Insert a decision record with options and pros/cons',
      icon: 'Scale',
      group: 'blocks',
      keywords: ['decision', 'adr', 'choose', 'option', 'vote', 'pros', 'cons'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'decision',
              data: JSON.stringify({
                title: 'Untitled Decision',
                type: 'binary',
                status: 'open',
                options: [
                  { id: 'opt-1', label: 'Option A', pros: [], cons: [] },
                  { id: 'opt-2', label: 'Option B', pros: [], cons: [] },
                ],
                linkedIssueIds: [],
              }),
              version: 1,
            },
          })
          .run(),
    },
    {
      name: 'form',
      label: 'Form',
      description: 'Insert an interactive form with validation',
      icon: 'ClipboardList',
      group: 'blocks',
      keywords: ['form', 'input', 'survey', 'questionnaire', 'fields'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'form',
              data: JSON.stringify({
                title: 'Untitled Form',
                description: '',
                fields: [{ id: 'f-1', type: 'text', label: 'Field 1', required: true }],
                responses: [],
              }),
              version: 1,
            },
          })
          .run(),
    },
    {
      name: 'raci',
      label: 'RACI Matrix',
      description: 'Insert a RACI responsibility matrix',
      icon: 'Grid3X3',
      group: 'blocks',
      keywords: ['raci', 'responsibility', 'matrix', 'accountable', 'consulted', 'informed'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'raci',
              data: JSON.stringify({
                title: 'RACI Matrix',
                stakeholders: ['Person A', 'Person B'],
                deliverables: [{ id: 'd-1', name: 'Deliverable 1', assignments: {} }],
              }),
              version: 1,
            },
          })
          .run(),
    },
    {
      name: 'risk',
      label: 'Risk Register',
      description: 'Insert a risk register with scoring',
      icon: 'ShieldAlert',
      group: 'blocks',
      keywords: ['risk', 'register', 'probability', 'impact', 'mitigation'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'risk',
              data: JSON.stringify({
                title: 'Risk Register',
                risks: [
                  {
                    id: 'r-1',
                    description: 'Risk 1',
                    probability: 3,
                    impact: 3,
                    mitigation: '',
                    strategy: 'mitigate',
                    owner: '',
                  },
                ],
              }),
              version: 1,
            },
          })
          .run(),
    },
    {
      name: 'timeline',
      label: 'Timeline',
      description: 'Insert a project timeline with milestones',
      icon: 'CalendarClock',
      group: 'blocks',
      keywords: ['timeline', 'milestone', 'schedule', 'roadmap', 'gantt'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'timeline',
              data: JSON.stringify({
                title: 'Project Timeline',
                milestones: [
                  {
                    id: 'm-1',
                    name: 'Milestone 1',
                    date: '',
                    status: 'on-track',
                    dependencies: [],
                  },
                ],
              }),
              version: 1,
            },
          })
          .run(),
    },
    {
      name: 'dashboard',
      label: 'KPI Dashboard',
      description: 'Insert a KPI dashboard with metrics',
      icon: 'BarChart3',
      group: 'blocks',
      keywords: ['dashboard', 'kpi', 'metric', 'chart', 'widget'],
      execute: (editor) =>
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'pmBlock',
            attrs: {
              blockType: 'dashboard',
              data: JSON.stringify({
                title: 'KPI Dashboard',
                widgets: [{ id: 'w-1', metric: 'Metric 1', value: 0, trend: 'flat', unit: '' }],
              }),
              version: 1,
            },
          })
          .run(),
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

    // Media commands
    {
      name: 'video',
      label: 'Video',
      description: 'Embed a YouTube or Vimeo video',
      icon: 'Play',
      group: 'media',
      keywords: ['youtube', 'vimeo', 'embed', 'video', 'media', 'watch'],
      execute: (editor) => {
        showVideoUrlPrompt(editor, (url) => {
          const platform = isVideoUrl(url);
          if (platform === 'youtube') {
            editor.chain().focus().setYoutubeVideo({ src: url }).run();
          } else if (platform === 'vimeo') {
            const id = extractVimeoId(url);
            if (id) {
              editor
                .chain()
                .focus()
                .insertContent({
                  type: 'vimeo',
                  attrs: { src: `https://player.vimeo.com/video/${id}` },
                })
                .run();
            } else {
              toast.error('Please enter a valid YouTube or Vimeo URL');
            }
          } else {
            toast.error('Please enter a valid YouTube or Vimeo URL');
          }
        });
      },
    },
    {
      name: 'image',
      label: 'Image',
      description: 'Insert an image with caption',
      icon: 'Image',
      group: 'media',
      keywords: ['photo', 'picture', 'figure', 'upload'],
      execute: (editor) => {
        openFilePicker('image/*', (files) => {
          for (const file of files) {
            editor.commands.insertContent({
              type: 'figure',
              attrs: {
                src: null,
                alt: file.name,
                artifactId: null,
                status: 'uploading',
              },
              content: [],
            });
            // Fire upload event for config.ts event listener to pick up
            const event = new CustomEvent('pilot:upload-artifact', {
              detail: { file, nodeType: 'figure', editor },
              bubbles: true,
            });
            editor.view.dom.dispatchEvent(event);
          }
        });
      },
    },
    {
      name: 'file',
      label: 'File',
      description: 'Attach a file as an inline card',
      icon: 'Paperclip',
      group: 'media',
      keywords: ['attach', 'upload', 'document', 'card'],
      execute: (editor) => {
        openFilePicker(
          'image/*,application/pdf,text/*,application/json,application/vnd.ms-excel,text/csv',
          (files) => {
            for (const file of files) {
              editor.commands.insertContent({
                type: 'fileCard',
                attrs: {
                  artifactId: null,
                  filename: file.name,
                  mimeType: file.type,
                  sizeBytes: file.size,
                  status: 'uploading',
                },
              });
              const event = new CustomEvent('pilot:upload-artifact', {
                detail: { file, nodeType: 'fileCard', editor },
                bubbles: true,
              });
              editor.view.dom.dispatchEvent(event);
            }
          }
        );
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
