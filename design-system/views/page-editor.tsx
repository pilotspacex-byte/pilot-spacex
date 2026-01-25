/**
 * Page/Documentation Editor Component
 *
 * Rich text editor for documentation pages with AI assistance.
 * Follows Web Interface Guidelines:
 * - Autosave within 5 seconds (FR-007)
 * - Rich text formatting support
 * - AI content clearly labeled
 * - Proper keyboard shortcuts
 *
 * SECURITY NOTE: This component is designed as a mockup/design specification.
 * In production, content MUST be sanitized using DOMPurify or similar library
 * before rendering. The actual implementation should use TipTap editor which
 * handles content safely.
 */

import * as React from 'react';
import {
  IconBold,
  IconItalic,
  IconUnderline,
  IconStrikethrough,
  IconCode,
  IconH1,
  IconH2,
  IconH3,
  IconList,
  IconListNumbers,
  IconQuote,
  IconLink,
  IconPhoto,
  IconTable,
  IconSparkles,
  IconDeviceFloppy,
  IconClock,
  IconDots,
  IconTrash,
  IconHistory,
  IconShare,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Button } from '../components/button';
import { AIBadge } from '../components/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/dialog';

// =============================================================================
// TYPES
// =============================================================================

export interface Page {
  id: string;
  title: string;
  content: string; // HTML or markdown - MUST be sanitized before render
  parentId?: string;
  createdAt: Date;
  updatedAt: Date;
  createdBy: {
    name: string;
    avatarUrl?: string;
  };
  lastEditedBy?: {
    name: string;
    avatarUrl?: string;
  };
}

export interface PageEditorProps {
  page: Page;
  onSave: (content: { title: string; content: string }) => Promise<void>;
  onDelete?: () => void;
  onGenerateAI?: (prompt: string) => Promise<string>;
  isReadOnly?: boolean;
  /**
   * Sanitize function - REQUIRED in production.
   * Use DOMPurify.sanitize or equivalent.
   */
  sanitizeHtml?: (html: string) => string;
}

// =============================================================================
// TOOLBAR
// =============================================================================

interface ToolbarButtonProps {
  icon: typeof IconBold;
  label: string;
  isActive?: boolean;
  onClick: () => void;
  shortcut?: string;
}

function ToolbarButton({
  icon: Icon,
  label,
  isActive,
  onClick,
  shortcut,
}: ToolbarButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
        'hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive && 'bg-accent text-accent-foreground'
      )}
      aria-label={label}
      aria-pressed={isActive}
      title={shortcut ? `${label} (${shortcut})` : label}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

interface EditorToolbarProps {
  onFormat: (format: string) => void;
  onInsert: (type: string) => void;
  onAIGenerate: () => void;
  activeFormats: string[];
}

function EditorToolbar({
  onFormat,
  onInsert,
  onAIGenerate,
  activeFormats,
}: EditorToolbarProps) {
  return (
    <div className="flex items-center gap-1 border-b bg-muted/30 p-2">
      {/* Text formatting */}
      <div className="flex items-center gap-0.5">
        <ToolbarButton
          icon={IconBold}
          label="Bold"
          shortcut="Cmd+B"
          isActive={activeFormats.includes('bold')}
          onClick={() => onFormat('bold')}
        />
        <ToolbarButton
          icon={IconItalic}
          label="Italic"
          shortcut="Cmd+I"
          isActive={activeFormats.includes('italic')}
          onClick={() => onFormat('italic')}
        />
        <ToolbarButton
          icon={IconUnderline}
          label="Underline"
          shortcut="Cmd+U"
          isActive={activeFormats.includes('underline')}
          onClick={() => onFormat('underline')}
        />
        <ToolbarButton
          icon={IconStrikethrough}
          label="Strikethrough"
          isActive={activeFormats.includes('strike')}
          onClick={() => onFormat('strike')}
        />
        <ToolbarButton
          icon={IconCode}
          label="Code"
          shortcut="Cmd+E"
          isActive={activeFormats.includes('code')}
          onClick={() => onFormat('code')}
        />
      </div>

      <div className="mx-2 h-6 w-px bg-border" />

      {/* Headings */}
      <div className="flex items-center gap-0.5">
        <ToolbarButton
          icon={IconH1}
          label="Heading 1"
          isActive={activeFormats.includes('h1')}
          onClick={() => onFormat('h1')}
        />
        <ToolbarButton
          icon={IconH2}
          label="Heading 2"
          isActive={activeFormats.includes('h2')}
          onClick={() => onFormat('h2')}
        />
        <ToolbarButton
          icon={IconH3}
          label="Heading 3"
          isActive={activeFormats.includes('h3')}
          onClick={() => onFormat('h3')}
        />
      </div>

      <div className="mx-2 h-6 w-px bg-border" />

      {/* Lists and blocks */}
      <div className="flex items-center gap-0.5">
        <ToolbarButton
          icon={IconList}
          label="Bullet list"
          isActive={activeFormats.includes('bulletList')}
          onClick={() => onFormat('bulletList')}
        />
        <ToolbarButton
          icon={IconListNumbers}
          label="Numbered list"
          isActive={activeFormats.includes('orderedList')}
          onClick={() => onFormat('orderedList')}
        />
        <ToolbarButton
          icon={IconQuote}
          label="Quote"
          isActive={activeFormats.includes('blockquote')}
          onClick={() => onFormat('blockquote')}
        />
      </div>

      <div className="mx-2 h-6 w-px bg-border" />

      {/* Inserts */}
      <div className="flex items-center gap-0.5">
        <ToolbarButton
          icon={IconLink}
          label="Insert link"
          shortcut="Cmd+K"
          onClick={() => onInsert('link')}
        />
        <ToolbarButton
          icon={IconPhoto}
          label="Insert image"
          onClick={() => onInsert('image')}
        />
        <ToolbarButton
          icon={IconTable}
          label="Insert table"
          onClick={() => onInsert('table')}
        />
        <ToolbarButton
          icon={IconCode}
          label="Insert code block"
          onClick={() => onInsert('codeBlock')}
        />
      </div>

      <div className="mx-2 h-6 w-px bg-border" />

      {/* AI Generate */}
      <Button
        variant="ai"
        size="sm"
        onClick={onAIGenerate}
        className="ml-auto"
      >
        <IconSparkles className="mr-1 h-4 w-4" />
        AI Generate
      </Button>
    </div>
  );
}

// =============================================================================
// AI GENERATION MODAL
// =============================================================================

interface AIGenerateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (prompt: string) => Promise<void>;
  isGenerating: boolean;
}

function AIGenerateModal({
  open,
  onOpenChange,
  onGenerate,
  isGenerating,
}: AIGenerateModalProps) {
  const [prompt, setPrompt] = React.useState('');
  const [generationType, setGenerationType] = React.useState<
    'documentation' | 'diagram' | 'summary' | 'expand'
  >('documentation');

  const handleGenerate = async () => {
    await onGenerate(`[${generationType}] ${prompt}`);
    setPrompt('');
    onOpenChange(false);
  };

  const suggestions = [
    { type: 'documentation' as const, label: 'Generate documentation', placeholder: 'Describe the feature or code to document...' },
    { type: 'diagram' as const, label: 'Generate diagram', placeholder: 'Describe the system architecture or flow...' },
    { type: 'summary' as const, label: 'Summarize content', placeholder: 'Paste content to summarize...' },
    { type: 'expand' as const, label: 'Expand section', placeholder: 'Describe what to elaborate on...' },
  ];

  const currentSuggestion = suggestions.find((s) => s.type === generationType);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <IconSparkles className="h-5 w-5 text-ai-suggestion" />
            AI Content Generation
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Generation type */}
          <div className="flex gap-2">
            {suggestions.map((s) => (
              <button
                key={s.type}
                onClick={() => setGenerationType(s.type)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  generationType === s.type
                    ? 'bg-ai-suggestion text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Prompt input */}
          <div>
            <label htmlFor="ai-prompt" className="mb-1 block text-sm font-medium">
              Describe what you want to generate
            </label>
            <textarea
              id="ai-prompt"
              className={cn(
                'flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2',
                'text-sm ring-offset-background placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
              placeholder={currentSuggestion?.placeholder}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          {/* AI disclaimer */}
          <div className="flex items-start gap-2 rounded-md bg-ai-suggestion/10 p-3 text-sm">
            <AIBadge type="generated" />
            <p className="text-muted-foreground">
              AI-generated content will be clearly marked. Review and edit before publishing.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            loading={isGenerating}
            disabled={!prompt.trim()}
          >
            Generate Content
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// MAIN EDITOR COMPONENT
// =============================================================================

/**
 * Default identity sanitizer - FOR DESIGN MOCKUP ONLY.
 * In production, replace with DOMPurify.sanitize
 */
const defaultSanitizer = (html: string) => {
  // WARNING: This is NOT safe for production use!
  // In production, use: import DOMPurify from 'dompurify';
  // return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
  console.warn('PageEditor: Using default sanitizer. Use DOMPurify in production!');
  return html;
};

export function PageEditor({
  page,
  onSave,
  onDelete,
  onGenerateAI,
  isReadOnly = false,
  sanitizeHtml = defaultSanitizer,
}: PageEditorProps) {
  const [title, setTitle] = React.useState(page.title);
  const [content, setContent] = React.useState(page.content);
  const [isSaving, setIsSaving] = React.useState(false);
  const [lastSaved, setLastSaved] = React.useState<Date | null>(null);
  const [isDirty, setIsDirty] = React.useState(false);
  const [activeFormats, setActiveFormats] = React.useState<string[]>([]);
  const [showAIModal, setShowAIModal] = React.useState(false);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [showMoreMenu, setShowMoreMenu] = React.useState(false);

  const editorRef = React.useRef<HTMLDivElement>(null);
  const autosaveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sanitized content for display
  const sanitizedContent = React.useMemo(
    () => sanitizeHtml(content),
    [content, sanitizeHtml]
  );

  // Track dirty state
  React.useEffect(() => {
    if (title !== page.title || content !== page.content) {
      setIsDirty(true);
    }
  }, [title, content, page.title, page.content]);

  // Autosave logic - save within 5 seconds of changes (FR-007)
  React.useEffect(() => {
    if (!isDirty || isReadOnly) return;

    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
    }

    autosaveTimerRef.current = setTimeout(async () => {
      setIsSaving(true);
      try {
        await onSave({ title, content });
        setLastSaved(new Date());
        setIsDirty(false);
      } catch (error) {
        console.error('Autosave failed:', error);
      } finally {
        setIsSaving(false);
      }
    }, 3000); // 3 second debounce

    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, [title, content, isDirty, isReadOnly, onSave]);

  // Handle format commands
  const handleFormat = (format: string) => {
    // In a real implementation, this would use TipTap or similar
    document.execCommand(
      format === 'h1' ? 'formatBlock' :
      format === 'h2' ? 'formatBlock' :
      format === 'h3' ? 'formatBlock' :
      format === 'bulletList' ? 'insertUnorderedList' :
      format === 'orderedList' ? 'insertOrderedList' :
      format === 'blockquote' ? 'formatBlock' :
      format,
      false,
      format.startsWith('h') ? `<${format}>` : undefined
    );
  };

  // Handle insert commands
  const handleInsert = (type: string) => {
    // Placeholder for insert functionality
    console.log('Insert:', type);
  };

  // Handle AI generation
  const handleAIGenerate = async (prompt: string) => {
    if (!onGenerateAI) return;

    setIsGenerating(true);
    try {
      const generatedContent = await onGenerateAI(prompt);
      // Insert generated content with AI marker
      setContent((prev) => prev + '\n\n' + generatedContent);
    } finally {
      setIsGenerating(false);
    }
  };

  // Manual save
  const handleManualSave = async () => {
    setIsSaving(true);
    try {
      await onSave({ title, content });
      setLastSaved(new Date());
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  };

  // Format last saved time
  const formatLastSaved = () => {
    if (!lastSaved) return null;
    const now = new Date();
    const diff = Math.floor((now.getTime() - lastSaved.getTime()) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(lastSaved);
  };

  // Handle content change from contentEditable
  const handleContentChange = React.useCallback(() => {
    if (editorRef.current) {
      setContent(editorRef.current.innerHTML);
    }
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          {/* Save status */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {isSaving ? (
              <>
                <IconDeviceFloppy className="h-4 w-4 animate-pulse" />
                <span>Saving...</span>
              </>
            ) : isDirty ? (
              <>
                <IconClock className="h-4 w-4" />
                <span>Unsaved changes</span>
              </>
            ) : lastSaved ? (
              <>
                <IconDeviceFloppy className="h-4 w-4" />
                <span>Saved {formatLastSaved()}</span>
              </>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualSave}
            disabled={!isDirty || isSaving}
          >
            Save
          </Button>

          {/* More menu */}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              aria-label="More options"
            >
              <IconDots className="h-4 w-4" />
            </Button>

            {showMoreMenu && (
              <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-md border bg-popover py-1 shadow-lg">
                <button
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                  onClick={() => {
                    setShowMoreMenu(false);
                    // Show history
                  }}
                >
                  <IconHistory className="h-4 w-4" />
                  View history
                </button>
                <button
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                  onClick={() => {
                    setShowMoreMenu(false);
                    // Share page
                  }}
                >
                  <IconShare className="h-4 w-4" />
                  Share
                </button>
                {onDelete && (
                  <>
                    <div className="my-1 border-t" />
                    <button
                      className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-accent"
                      onClick={() => {
                        setShowMoreMenu(false);
                        onDelete();
                      }}
                    >
                      <IconTrash className="h-4 w-4" />
                      Delete page
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toolbar */}
      {!isReadOnly && (
        <EditorToolbar
          onFormat={handleFormat}
          onInsert={handleInsert}
          onAIGenerate={() => setShowAIModal(true)}
          activeFormats={activeFormats}
        />
      )}

      {/* Editor area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          {/* Title */}
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled"
            className={cn(
              'mb-6 w-full bg-transparent text-3xl font-bold',
              'placeholder:text-muted-foreground/50',
              'focus:outline-none',
              isReadOnly && 'cursor-default'
            )}
            readOnly={isReadOnly}
          />

          {/* Content editor - NOTE: In production use TipTap */}
          <div
            ref={editorRef}
            contentEditable={!isReadOnly}
            suppressContentEditableWarning
            className={cn(
              'prose prose-zinc dark:prose-invert max-w-none',
              'min-h-[400px]',
              'focus:outline-none',
              '[&_[data-ai-generated]]:border-l-2 [&_[data-ai-generated]]:border-ai-suggestion [&_[data-ai-generated]]:bg-ai-suggestion/5 [&_[data-ai-generated]]:pl-4'
            )}
            onInput={handleContentChange}
            onKeyDown={(e) => {
              // Keyboard shortcuts
              if (e.metaKey || e.ctrlKey) {
                if (e.key === 'b') {
                  e.preventDefault();
                  handleFormat('bold');
                } else if (e.key === 'i') {
                  e.preventDefault();
                  handleFormat('italic');
                } else if (e.key === 'u') {
                  e.preventDefault();
                  handleFormat('underline');
                } else if (e.key === 's') {
                  e.preventDefault();
                  handleManualSave();
                }
              }
            }}
          >
            {/* Initial content rendered as text for safety - TipTap handles this properly */}
            {sanitizedContent}
          </div>

          {/* Page metadata */}
          <div className="mt-8 border-t pt-4 text-sm text-muted-foreground">
            <p>
              Created by {page.createdBy.name} on{' '}
              {new Intl.DateTimeFormat('en-US', {
                dateStyle: 'medium',
                timeStyle: 'short',
              }).format(page.createdAt)}
            </p>
            {page.lastEditedBy && (
              <p>
                Last edited by {page.lastEditedBy.name} on{' '}
                {new Intl.DateTimeFormat('en-US', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                }).format(page.updatedAt)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* AI Generate Modal */}
      <AIGenerateModal
        open={showAIModal}
        onOpenChange={setShowAIModal}
        onGenerate={handleAIGenerate}
        isGenerating={isGenerating}
      />
    </div>
  );
}
