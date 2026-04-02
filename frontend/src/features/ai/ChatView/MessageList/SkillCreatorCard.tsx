/**
 * SkillCreatorCard — inline skill preview and editor card in ChatView.
 *
 * Renders skill name, frontmatter description, and SKILL.md content.
 * Edit/Preview opens a large modal dialog with CodeMirror 6 editor.
 * Has Save and Test action buttons.
 *
 * CRITICAL: Must NOT be observer() — CodeMirror inside a MobX tracking scope causes
 * the same flushSync/React 19 issue as TipTap. Use React.memo + local useState.
 *
 * Phase 64-03
 */
'use client';

import { memo, useState, useEffect, useRef } from 'react';
import { Wand2, Pencil, Eye, PlayCircle, Save, CheckCircle, Maximize2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// CodeMirror 6 — per locked user decision (not Monaco, not textarea)
import { EditorView } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { markdown } from '@codemirror/lang-markdown';
import { basicSetup } from 'codemirror';

interface SkillCodeMirrorEditorProps {
  value: string;
  onChange: (v: string) => void;
  maxHeight?: string;
}

/**
 * Thin CodeMirror 6 wrapper for markdown editing.
 * Mounted once via useEffect; external content changes are NOT synced back
 * (content flows out via onChange callback only).
 * NOT observer() — lives outside MobX tracking.
 */
function SkillCodeMirrorEditor({ value, onChange, maxHeight = '250px' }: SkillCodeMirrorEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        markdown(),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChange(update.state.doc.toString());
          }
        }),
        EditorView.theme({
          '&': { maxHeight, fontSize: '13px' },
          '.cm-scroller': { overflow: 'auto', fontFamily: 'JetBrains Mono, monospace' },
          '.cm-content': { padding: '12px' },
        }),
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // Mount once — content flows out via onChange
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={containerRef} data-testid="codemirror-editor" />;
}

export interface SkillCreatorCardProps {
  skillName: string;
  frontmatter: Record<string, string>;
  content: string;
  isUpdate: boolean;
  onSave?: (content: string) => void;
  onTest?: (content: string) => void;
  /** When true, Save button shows loading state */
  isSaving?: boolean;
  /** When true, card shows saved confirmation state */
  isSaved?: boolean;
}

/**
 * SkillCreatorCard — chat card for reviewing and editing a generated skill.
 *
 * memo() wrapper ensures no MobX observer() — CodeMirror 6 must be outside
 * MobX tracking to avoid nested flushSync errors in React 19.
 */
export const SkillCreatorCard = memo<SkillCreatorCardProps>(function SkillCreatorCard({
  skillName,
  frontmatter,
  content,
  isUpdate,
  onSave,
  onTest,
  isSaving = false,
  isSaved = false,
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  // Track user edits separately; when not editing, display prop content directly.
  const [editedContent, setEditedContent] = useState(content);
  const displayContent = isEditing ? editedContent : content;

  return (
    <>
      <div
        className="mx-4 my-3 rounded-[14px] border bg-background p-4 animate-fade-up"
        role="article"
        aria-label={`Skill preview: ${skillName}`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <Wand2 className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="font-medium text-sm font-mono">{skillName}</span>
          {isSaved ? (
            <Badge variant="outline" className="text-green-600 border-green-600/30 bg-green-50">
              <CheckCircle className="h-3 w-3 mr-1" aria-hidden="true" />
              Saved
            </Badge>
          ) : isUpdate ? (
            <Badge variant="outline">Updated</Badge>
          ) : (
            <Badge variant="outline" className="text-green-600 border-green-600/30">
              New
            </Badge>
          )}
        </div>

        {/* Description */}
        {frontmatter.description && (
          <p className="text-sm text-muted-foreground mb-3">{frontmatter.description}</p>
        )}

        {/* Compact content preview — click to open modal */}
        <button
          type="button"
          className="w-full text-left rounded-lg border bg-muted/50 mb-3 max-h-[120px] overflow-hidden relative cursor-pointer hover:bg-muted/70 transition-colors"
          onClick={() => setModalOpen(true)}
          aria-label="Expand skill content"
        >
          <pre className="text-xs font-mono whitespace-pre-wrap p-3 leading-relaxed">
            {displayContent.slice(0, 300)}
            {displayContent.length > 300 && '...'}
          </pre>
          <div className="absolute bottom-0 inset-x-0 h-8 bg-gradient-to-t from-muted/80 to-transparent flex items-end justify-center pb-1">
            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Maximize2 className="h-3 w-3" />
              Click to expand
            </span>
          </div>
        </button>

        {/* Footer actions — hidden after save */}
        {!isSaved && (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setModalOpen(true);
                setIsEditing(true);
              }}
              aria-label="Edit skill in modal"
            >
              <Pencil className="h-3 w-3 mr-1" aria-hidden="true" />
              Edit
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onTest?.(displayContent)}
              aria-label="Test this skill"
            >
              <PlayCircle className="h-3 w-3 mr-1" aria-hidden="true" />
              Test
            </Button>
            <Button
              size="sm"
              onClick={() => onSave?.(displayContent)}
              aria-label="Save this skill"
              disabled={isSaving}
            >
              <Save className="h-3 w-3 mr-1" aria-hidden="true" />
              {isSaving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        )}
      </div>

      {/* Large editing/preview modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <Wand2 className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
                <DialogTitle className="truncate font-mono">{skillName}</DialogTitle>
                {isSaved ? (
                  <Badge variant="outline" className="text-green-600 border-green-600/30 bg-green-50 shrink-0">
                    <CheckCircle className="h-3 w-3 mr-1" aria-hidden="true" />
                    Saved
                  </Badge>
                ) : isUpdate ? (
                  <Badge variant="outline" className="shrink-0">Updated</Badge>
                ) : (
                  <Badge variant="outline" className="text-green-600 border-green-600/30 shrink-0">New</Badge>
                )}
              </div>
              {!isSaved && (
                <div className="flex gap-1.5 shrink-0">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditing((prev) => !prev)}
                  >
                    {isEditing ? (
                      <><Eye className="h-3.5 w-3.5 mr-1.5" />Preview</>
                    ) : (
                      <><Pencil className="h-3.5 w-3.5 mr-1.5" />Edit</>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      onTest?.(displayContent);
                      setModalOpen(false);
                    }}
                  >
                    <PlayCircle className="h-3.5 w-3.5 mr-1.5" />
                    Test
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => onSave?.(displayContent)}
                    disabled={isSaving}
                  >
                    <Save className="h-3.5 w-3.5 mr-1.5" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              )}
            </div>
            {frontmatter.description && (
              <p className="text-sm text-muted-foreground mt-1.5">{frontmatter.description}</p>
            )}
          </DialogHeader>

          <div className="flex-1 overflow-y-auto">
            {isEditing ? (
              <SkillCodeMirrorEditor
                value={editedContent}
                onChange={setEditedContent}
                maxHeight="60vh"
              />
            ) : (
              <pre className="text-sm font-mono whitespace-pre-wrap p-6 leading-relaxed">
                {displayContent}
              </pre>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});

SkillCreatorCard.displayName = 'SkillCreatorCard';
