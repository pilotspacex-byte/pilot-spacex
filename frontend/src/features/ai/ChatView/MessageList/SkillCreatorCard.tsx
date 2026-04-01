/**
 * SkillCreatorCard — inline skill preview and editor card in ChatView.
 *
 * Renders skill name, frontmatter description, and SKILL.md content.
 * Provides Edit/Preview toggle with CodeMirror 6 editor (NOT Monaco, NOT textarea).
 * Has Save and Test action buttons.
 *
 * CRITICAL: Must NOT be observer() — CodeMirror inside a MobX tracking scope causes
 * the same flushSync/React 19 issue as TipTap. Use React.memo + local useState.
 *
 * Phase 64-03
 */
'use client';

import { memo, useState, useEffect, useRef } from 'react';
import { Wand2, Pencil, Eye, PlayCircle, Save, CheckCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

// CodeMirror 6 — per locked user decision (not Monaco, not textarea)
import { EditorView } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { markdown } from '@codemirror/lang-markdown';
import { basicSetup } from 'codemirror';

interface SkillCodeMirrorEditorProps {
  value: string;
  onChange: (v: string) => void;
}

/**
 * Thin CodeMirror 6 wrapper for markdown editing.
 * Mounted once via useEffect; external content changes are NOT synced back
 * (content flows out via onChange callback only).
 * NOT observer() — lives outside MobX tracking.
 */
function SkillCodeMirrorEditor({ value, onChange }: SkillCodeMirrorEditorProps) {
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
          '&': { maxHeight: '250px', fontSize: '13px' },
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
  const [isEditing, setIsEditing] = useState(false);
  const [localContent, setLocalContent] = useState(content);

  // Sync from props when content changes externally (e.g., store update)
  useEffect(() => {
    setLocalContent(content);
  }, [content]);

  return (
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

      {/* Content — read mode or CodeMirror edit mode */}
      <div className="rounded-lg border bg-muted/50 mb-3 max-h-[300px] overflow-auto">
        {isEditing ? (
          <SkillCodeMirrorEditor value={localContent} onChange={setLocalContent} />
        ) : (
          <pre className="text-sm font-mono whitespace-pre-wrap p-3 leading-relaxed">
            {localContent}
          </pre>
        )}
      </div>

      {/* Footer actions — hidden after save */}
      {!isSaved && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsEditing((prev) => !prev)}
            aria-label={isEditing ? 'Switch to preview mode' : 'Switch to edit mode'}
          >
            {isEditing ? (
              <Eye className="h-3 w-3 mr-1" aria-hidden="true" />
            ) : (
              <Pencil className="h-3 w-3 mr-1" aria-hidden="true" />
            )}
            {isEditing ? 'Preview' : 'Edit'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onTest?.(localContent)}
            aria-label="Test this skill"
          >
            <PlayCircle className="h-3 w-3 mr-1" aria-hidden="true" />
            Test
          </Button>
          <Button
            size="sm"
            onClick={() => onSave?.(localContent)}
            aria-label="Save this skill"
            disabled={isSaving}
          >
            <Save className="h-3 w-3 mr-1" aria-hidden="true" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      )}
    </div>
  );
});

SkillCreatorCard.displayName = 'SkillCreatorCard';
