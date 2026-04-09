/**
 * ChatInput - Compact auto-resizing contenteditable input with skill/agent menus
 * Follows shadcn/ui AI prompt input component pattern
 */

import { useCallback, useState, useRef, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Sparkles, AtSign, History, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  NoteContext,
  IssueContext,
  ProjectContext,
  SkillDefinition,
  AgentDefinition,
} from '../types';
import { TokenBudgetRing } from '@/components/ui/token-budget-ring';
import { ContextIndicator } from './ContextIndicator';
import { SkillMenu } from './SkillMenu';
import { useSkills } from '../hooks/useSkills';
import { AgentMenu } from './AgentMenu';
import { SectionMenu } from './SectionMenu';
import { SessionResumeMenu, type SessionSummary } from './SessionResumeMenu';
import type { HeadingItem } from '@/components/editor/AutoTOC';
import { WorkingIndicator } from './WorkingIndicator';
import { useAttachments } from '../hooks/useAttachments';
import { useDriveStatus } from '../hooks/useDriveStatus';
import { AttachmentButton } from './AttachmentButton';
import { DriveFilePicker } from './DriveFilePicker';
import { RecordButton } from './RecordButton';
import { AudioPlaybackPill } from './AudioPlaybackPill';
import { attachmentsApi } from '@/services/api/attachments';
import { EntityPicker } from './EntityPicker';
import { useRecentEntities } from '../hooks/useRecentEntities';
import type { RecentEntity } from '../hooks/useRecentEntities';

/**
 * Recursively walks a contenteditable node tree to produce a serialized string.
 * Text nodes emit raw text; chip spans (with data-entity-type) emit @[Type:uuid];
 * <br> elements and block element boundaries (DIV, P) emit a newline character.
 * This ensures Shift+Enter-produced line breaks are preserved in the serialized value.
 */
function serializeNode(node: Node, isRoot = false): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent ?? '';
  }
  if (node instanceof HTMLElement) {
    // Chip span — emit token directly (do not recurse into its children)
    if (node.dataset.entityType) {
      return `@[${node.dataset.entityType}:${node.dataset.entityId}]`;
    }
    // <br> — emit a newline
    if (node.tagName === 'BR') {
      return '\n';
    }
    // Block elements (DIV, P) produced by contenteditable wrap lines
    const isBlock = node.tagName === 'DIV' || node.tagName === 'P';
    let inner = '';
    for (const child of Array.from(node.childNodes)) {
      inner += serializeNode(child);
    }
    // Prefix a newline for non-root block elements so each nested div/p becomes a new line
    return isBlock && !isRoot ? '\n' + inner : inner;
  }
  return '';
}

function getSerializedValue(div: HTMLDivElement): string {
  return serializeNode(div, true);
}

// Helper: get text content before cursor in contenteditable (module-scope like getSerializedValue)
function getTextBeforeCursor(div: HTMLDivElement): string {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return '';
  const range = sel.getRangeAt(0).cloneRange();
  range.selectNodeContents(div);
  range.setEnd(sel.getRangeAt(0).startContainer, sel.getRangeAt(0).startOffset);
  return range.toString();
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (payload: {
    attachmentIds: string[];
    attachments: Array<{ attachmentId: string; filename: string; mimeType: string; sizeBytes: number; source: 'local' | 'google_drive' }>;
    voiceAudioUrl?: string | null;
  }) => void;
  isStreaming?: boolean;
  isDisabled?: boolean;
  autoFocus?: boolean;
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  /** Token budget usage percentage (0-100) for budget ring display */
  tokenBudgetPercent?: number;
  /** Tokens used in current session */
  tokensUsed?: number;
  /** Total token budget */
  tokenBudget?: number;
  /** Sessions available for /resume command */
  sessions?: SessionSummary[];
  /** Loading state for sessions */
  sessionsLoading?: boolean;
  /** Callback when a session is selected from /resume menu */
  onSelectSession?: (sessionId: string) => void;
  /** Callback when session search is performed */
  onSearchSessions?: (query: string) => void;
  /** Callback when user requests a new session */
  onNewSession?: () => void;
  /** Headings from current note for # section menu */
  noteHeadings?: HeadingItem[];
  /** Callback when user selects a section from # menu */
  onSelectSection?: (heading: HeadingItem) => void;
  /** Workspace ID for attachment uploads */
  workspaceId?: string;
  /** Session ID for attachment uploads */
  sessionId?: string;
  className?: string;
}

export const ChatInput = observer<ChatInputProps>(
  ({
    value,
    onChange,
    onSubmit,
    isStreaming = false,
    isDisabled = false,
    autoFocus = false,
    noteContext,
    issueContext,
    projectContext,
    onClearNoteContext,
    onClearIssueContext,
    tokenBudgetPercent,
    tokensUsed,
    tokenBudget = 8000,
    sessions = [],
    sessionsLoading = false,
    onSelectSession,
    onSearchSessions,
    onNewSession,
    onClearProjectContext,
    noteHeadings,
    onSelectSection,
    workspaceId,
    sessionId,
    className,
  }) => {
    const { skills: dynamicSkills } = useSkills(workspaceId);
    const { attachments, attachmentIds, addFile, addFromDrive, removeFile, reset } = useAttachments(
      {
        workspaceId: workspaceId ?? '',
        sessionId,
      }
    );
    const { data: driveStatus } = useDriveStatus(workspaceId);
    const [drivePickerOpen, setDrivePickerOpen] = useState(false);
    const [isDragOver, setIsDragOver] = useState(false);
    const [pendingAudioUrl, setPendingAudioUrl] = useState<string | null>(null);
    // Text in input before live recording started — used to restore on cancel or prepend on commit
    const preRecordTextRef = useRef('');
    const editableRef = useRef<HTMLDivElement>(null);
    const inputContainerRef = useRef<HTMLDivElement>(null);
    const skillCommandRef = useRef<HTMLDivElement>(null);
    const entityCommandRef = useRef<HTMLDivElement>(null);
    const [skillMenuOpen, setSkillMenuOpen] = useState(false);
    const [agentMenuOpen, setAgentMenuOpen] = useState(false);
    const [sectionMenuOpen, setSectionMenuOpen] = useState(false);
    const [resumeMenuOpen, setResumeMenuOpen] = useState(false);
    const [inputWidth, setInputWidth] = useState<number | null>(null);

    // Slash query state — tracks text typed after '/' in the chat input
    const slashQueryStartOffsetRef = useRef<number | null>(null);
    const [slashQuery, setSlashQuery] = useState<string | null>(null);

    // When a skill close transitions to another menu (e.g. /resume),
    // skip the SkillMenu onOpenChange focus-restore to prevent the
    // deferred focus from closing the newly-opened menu.
    const skipFocusOnSkillCloseRef = useRef(false);

    // @ entity picker state (D-02)
    const atQueryStartOffsetRef = useRef<number | null>(null);
    const [atQuery, setAtQuery] = useState<string | null>(null);
    const [entityPickerOpen, setEntityPickerOpen] = useState(false);

    // Recent entities for picker (D-03)
    const { recentEntities, addEntity } = useRecentEntities(workspaceId ?? '');

    // Measure input container width for popover sizing
    useEffect(() => {
      if (inputContainerRef.current) {
        const resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            setInputWidth(entry.contentRect.width);
          }
        });
        resizeObserver.observe(inputContainerRef.current);
        return () => resizeObserver.disconnect();
      }
    }, []);

    // Auto-focus contenteditable when requested
    useEffect(() => {
      if (autoFocus && editableRef.current) {
        editableRef.current.focus();
      }
    }, [autoFocus]);

    // Sync contenteditable DOM when value prop changes (e.g., reset to '' after submit)
    useEffect(() => {
      if (!editableRef.current) return;
      const currentText = getSerializedValue(editableRef.current);
      if (value !== currentText) {
        editableRef.current.textContent = value;
      }
    }, [value]);

    // Detect #section trigger (only when note headings are available)
    useEffect(() => {
      if (!noteHeadings || noteHeadings.length === 0) return;
      const lastChar = value.slice(-1);
      const beforeLastChar = value.slice(-2, -1);

      if (lastChar === '#' && (beforeLastChar === '' || beforeLastChar === ' ')) {
        setSectionMenuOpen(true);
      }
    }, [value, noteHeadings]);

    const handleInput = useCallback(
      (e: React.FormEvent<HTMLDivElement>) => {
        const div = e.currentTarget;
        const serialized = getSerializedValue(div);
        onChange(serialized);

        // Slash trigger detection: track text after '/' at position 0 in first text node
        const sel = window.getSelection();
        if (sel && sel.rangeCount > 0) {
          // @ trigger detection for EntityPicker (D-02)
          const textBeforeCursor = getTextBeforeCursor(div);

          // Slash: if text before cursor starts with '/' and has no space (still in slash command)
          if (textBeforeCursor.startsWith('/') && !/\s/.test(textBeforeCursor)) {
            const query = textBeforeCursor.slice(1); // text typed after '/'
            slashQueryStartOffsetRef.current = 0;
            setSlashQuery(query);
            setSkillMenuOpen(true);
          } else if (skillMenuOpen) {
            // '/' prefix gone, or space was typed — close menu
            slashQueryStartOffsetRef.current = null;
            setSlashQuery(null);
            setSkillMenuOpen(false);
          }
          const atIdx = textBeforeCursor.lastIndexOf('@');
          if (atIdx >= 0 && !/\s/.test(textBeforeCursor.slice(atIdx + 1))) {
            const query = textBeforeCursor.slice(atIdx + 1);
            atQueryStartOffsetRef.current = atIdx;
            setAtQuery(query);
            setEntityPickerOpen(true);
          } else {
            atQueryStartOffsetRef.current = null;
            setAtQuery(null);
            setEntityPickerOpen(false);
          }
        }
      },
      [onChange, skillMenuOpen]
    );

    const handlePaste = useCallback(
      (e: React.ClipboardEvent<HTMLDivElement>) => {
        e.preventDefault();
        const text = e.clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
      },
      []
    );

    const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
        setIsDragOver(false);
      }
    }, []);

    const handleDrop = useCallback(
      (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragOver(false);
        const files = e.dataTransfer.files;
        for (const file of Array.from(files)) {
          void addFile(file);
        }
      },
      [addFile]
    );

    const handleConnectDrive = useCallback(async () => {
      if (!workspaceId) return;
      try {
        const callbackUrl = `${window.location.origin}/drive/callback`;
        const { auth_url } = await attachmentsApi.getDriveAuthUrl(workspaceId, callbackUrl);
        window.open(auth_url, '_blank', 'noopener,noreferrer');
        toast.success('Google OAuth tab opened — authorize and return here.');
      } catch {
        toast.error('Failed to get Google Drive authorization URL.');
      }
    }, [workspaceId]);

    const handleSkillSelect = useCallback(
      (skill: SkillDefinition) => {
        if (!editableRef.current) return;
        // Clear slash query state and close menu immediately
        setSlashQuery(null);
        setSkillMenuOpen(false);
        slashQueryStartOffsetRef.current = null;
        // Special handling for /resume - open session picker instead
        if (skill.name === 'resume') {
          editableRef.current.textContent = '';
          onChange('');
          skipFocusOnSkillCloseRef.current = true;
          setResumeMenuOpen(true);
          return;
        }
        // Special handling for /new - start fresh session
        if (skill.name === 'new') {
          editableRef.current.textContent = '';
          onChange('');
          onNewSession?.();
          editableRef.current.focus();
          return;
        }
        // Replace leading '/query' with '/skillname '
        const firstNode = editableRef.current.firstChild;
        if (firstNode?.nodeType === Node.TEXT_NODE) {
          firstNode.textContent = `/${skill.name} `;
        } else {
          editableRef.current.textContent = `/${skill.name} `;
        }
        onChange(`/${skill.name} `);
        // Defer focus + cursor placement so Radix's onCloseAutoFocus fires first
        setTimeout(() => {
          if (!editableRef.current) return;
          editableRef.current.focus();
          // Move cursor to end
          const range = document.createRange();
          range.selectNodeContents(editableRef.current);
          range.collapse(false);
          window.getSelection()?.removeAllRanges();
          window.getSelection()?.addRange(range);
        }, 0);
      },
      [onChange, onNewSession, setSkillMenuOpen]
    );

    const handleAgentSelect = useCallback(
      (agent: AgentDefinition) => {
        if (!editableRef.current) return;
        // Replace trailing '@' with '@agentname '
        const lastNode = editableRef.current.lastChild;
        if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('@')) {
          lastNode.textContent = lastNode.textContent.slice(0, -1) + `@${agent.name} `;
        } else {
          editableRef.current.textContent = (editableRef.current.textContent ?? '') + `@${agent.name} `;
        }
        onChange(getSerializedValue(editableRef.current));
        editableRef.current.focus();
        // Move cursor to end
        const range = document.createRange();
        range.selectNodeContents(editableRef.current);
        range.collapse(false);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      },
      [onChange]
    );

    const handleSectionSelect = useCallback(
      (heading: HeadingItem) => {
        if (!editableRef.current) return;
        // Remove the # trigger char from input
        const lastNode = editableRef.current.lastChild;
        if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('#')) {
          lastNode.textContent = lastNode.textContent.slice(0, -1).trim();
        }
        onChange(getSerializedValue(editableRef.current));
        onSelectSection?.(heading);
        editableRef.current.focus();
      },
      [onChange, onSelectSection]
    );

    const handleSessionSelect = useCallback(
      (sessionId: string) => {
        onSelectSession?.(sessionId);
        setResumeMenuOpen(false);
      },
      [onSelectSession]
    );

    const handleSkillCancel = useCallback(() => {
      setSlashQuery(null);
      slashQueryStartOffsetRef.current = null;
      editableRef.current?.focus();
    }, []);

    const handleSectionCancel = useCallback(() => {
      if (!editableRef.current) return;
      const lastNode = editableRef.current.lastChild;
      if (lastNode?.nodeType === Node.TEXT_NODE && lastNode.textContent?.endsWith('#')) {
        lastNode.textContent = lastNode.textContent.slice(0, -1);
      }
      onChange(getSerializedValue(editableRef.current));
      editableRef.current.focus();
    }, [onChange]);

    const handleEntitySelect = useCallback(
      (entity: RecentEntity) => {
        if (!editableRef.current) return;

        // 1. Build the chip DOM node (D-01 + D-07)
        const chip = document.createElement('span');
        chip.contentEditable = 'false';
        chip.setAttribute('data-entity-type', entity.type);
        chip.setAttribute('data-entity-id', entity.id);
        chip.textContent = `@${entity.title}`;
        chip.className =
          'inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.5 rounded-md ' +
          'bg-primary/10 text-primary text-xs font-medium select-none cursor-default';

        // 2. Find and remove '@{query}' text before cursor.
        // We must locate the @-trigger inside a Text node — Range.startOffset
        // means a child index when startContainer is an Element, not a character
        // offset. We walk back from the selection anchor to find a Text node that
        // contains the '@' trigger text and compute offsets within that node only.
        const sel = window.getSelection();
        let spaceNode: Text | null = null;
        if (sel && sel.rangeCount > 0) {
          try {
            const range = sel.getRangeAt(0);
            const atLen = 1 + (atQuery?.length ?? 0);

            // Resolve the Text node that holds the '@{query}' text
            let textNode: Text | null = null;
            let charOffset = 0;
            if (range.startContainer.nodeType === Node.TEXT_NODE) {
              textNode = range.startContainer as Text;
              charOffset = range.startOffset;
            } else if (range.startContainer instanceof Element) {
              // Caret is at a child-node boundary — inspect the child at startOffset - 1
              const child = range.startContainer.childNodes[range.startOffset - 1];
              if (child?.nodeType === Node.TEXT_NODE) {
                textNode = child as Text;
                charOffset = textNode.length;
              }
            }

            if (textNode !== null) {
              const deleteStart = Math.max(0, charOffset - atLen);
              range.setStart(textNode, deleteStart);
              range.setEnd(textNode, charOffset);
            }

            range.deleteContents();
            range.insertNode(chip);

            // 3. Insert trailing space after chip
            spaceNode = document.createTextNode(' ');
            range.setStartAfter(chip);
            range.collapse(true);
            range.insertNode(spaceNode);
          } catch {
            // DOMException guard — fall back: insert chip at cursor without deleting
            const range = sel.getRangeAt(0);
            range.insertNode(chip);
            spaceNode = document.createTextNode(' ');
            range.setStartAfter(chip);
            range.collapse(true);
            range.insertNode(spaceNode);
          }
        }

        // 4. Notify parent and update state (chip is in DOM at this point)
        onChange(getSerializedValue(editableRef.current));
        addEntity(entity);
        setAtQuery(null);
        setEntityPickerOpen(false);

        // 5. Place cursor after spaceNode (deferred so cmdk/Radix focus side-effects settle)
        const capturedSpaceNode = spaceNode;
        setTimeout(() => {
          if (!editableRef.current) return;
          editableRef.current.focus();
          if (capturedSpaceNode) {
            const newSel = window.getSelection();
            if (newSel) {
              const newRange = document.createRange();
              newRange.setStartAfter(capturedSpaceNode);
              newRange.collapse(true);
              newSel.removeAllRanges();
              newSel.addRange(newRange);
            }
          }
        }, 0);
      },
      [atQuery, onChange, addEntity]
    );

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLDivElement>) => {
        // Forward Arrow/Enter keys to cmdk root when a menu is open
        // cmdk's internal keyboard handler is bound to its root div, but focus stays in the
        // contenteditable (outside cmdk). Dispatching a native KeyboardEvent on the cmdk root
        // lets React 18 event delegation pick it up and fire cmdk's synthetic onKeyDown handler.
        if (skillMenuOpen || entityPickerOpen) {
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
            e.preventDefault();
            const targetRef = skillMenuOpen ? skillCommandRef : entityCommandRef;
            if (targetRef.current) {
              targetRef.current.dispatchEvent(
                new KeyboardEvent('keydown', {
                  key: e.key,
                  bubbles: true,
                  cancelable: true,
                })
              );
            }
            return;
          }
        }

        // Escape: close skill menu (before entity picker check)
        if (e.key === 'Escape' && skillMenuOpen) {
          e.preventDefault();
          setSkillMenuOpen(false);
          setSlashQuery(null);
          slashQueryStartOffsetRef.current = null;
          editableRef.current?.focus();
          return;
        }

        // Escape: close entity picker, leave @{query} text in place (D-02)
        if (e.key === 'Escape' && entityPickerOpen) {
          e.preventDefault();
          setEntityPickerOpen(false);
          editableRef.current?.focus();
          return;
        }

        // Backspace: remove chip when cursor is immediately after one.
        // Two cases for "caret immediately after chip":
        //   A) startContainer is a Text node at offset 0 → check previousSibling
        //   B) startContainer is the contenteditable Element → check childNodes[startOffset - 1]
        if (e.key === 'Backspace') {
          const sel = window.getSelection();
          if (sel && sel.rangeCount > 0) {
            const range = sel.getRangeAt(0);
            if (range.collapsed) {
              let chipCandidate: ChildNode | null = null;
              const container = range.startContainer;

              if (container === editableRef.current) {
                // Case B: startOffset is a child index
                chipCandidate = editableRef.current.childNodes[range.startOffset - 1] ?? null;
              } else if (range.startOffset === 0) {
                // Case A: caret at start of a text/element node
                chipCandidate =
                  container === editableRef.current
                    ? editableRef.current.lastChild
                    : container.previousSibling;
              }

              if (
                chipCandidate instanceof HTMLElement &&
                chipCandidate.dataset.entityType
              ) {
                e.preventDefault();
                chipCandidate.remove();
                onChange(getSerializedValue(editableRef.current!));
              }
            }
          }
        }

        if (
          e.key === 'Enter' &&
          !e.shiftKey &&
          !skillMenuOpen &&
          !agentMenuOpen &&
          !sectionMenuOpen &&
          !resumeMenuOpen &&
          !entityPickerOpen
        ) {
          e.preventDefault();
          const serialized = editableRef.current
            ? getSerializedValue(editableRef.current)
            : value;
          if (serialized.trim() && !isStreaming && !isDisabled) {
            const readyAttachments = attachments
              .filter((a) => a.status === 'ready' && a.attachmentId)
              .map((a) => ({
                attachmentId: a.attachmentId!,
                filename: a.filename,
                mimeType: a.mimeType,
                sizeBytes: a.sizeBytes,
                source: a.source,
              }));
            onSubmit({ attachmentIds, attachments: readyAttachments, voiceAudioUrl: pendingAudioUrl });
            setPendingAudioUrl(null);
            reset();
          }
        }
      },
      [
        value,
        isStreaming,
        isDisabled,
        skillMenuOpen,
        agentMenuOpen,
        sectionMenuOpen,
        resumeMenuOpen,
        entityPickerOpen,
        onSubmit,
        attachments,
        attachmentIds,
        pendingAudioUrl,
        reset,
        onChange,
      ]
    );

    return (
      <>
        <div
          className={cn('border-t bg-background relative', className)}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isDragOver && (
            <div
              className="absolute inset-0 z-20 flex items-center justify-center bg-background/80 border-2 border-dashed border-primary/50 rounded-lg pointer-events-none"
              data-testid="drop-overlay"
            >
              <span className="text-sm font-medium text-primary">Drop to attach</span>
            </div>
          )}
          <div className="px-3 pt-2 pb-3 space-y-2">
            {/* Context indicator */}
            <ContextIndicator
              noteContext={noteContext}
              issueContext={issueContext}
              projectContext={projectContext}
              onClearNoteContext={onClearNoteContext}
              onClearIssueContext={onClearIssueContext}
              onClearProjectContext={onClearProjectContext}
              attachments={attachments}
              onRemoveAttachment={removeFile}
            />

            {/* Audio playback pill — shown after voice transcription, before sending */}
            {pendingAudioUrl && (
              <AudioPlaybackPill
                audioUrl={pendingAudioUrl}
                onRemove={() => setPendingAudioUrl(null)}
              />
            )}

            {/* Input area - single container with inline toolbar */}
            <div className="relative" ref={inputContainerRef}>
              {/* Entity picker — positioned above the input via absolute bottom-full (D-06) */}
              <EntityPicker
                open={entityPickerOpen}
                onOpenChange={(open) => {
                  setEntityPickerOpen(open);
                  if (!open) {
                    setAtQuery(null);
                    atQueryStartOffsetRef.current = null;
                    setTimeout(() => editableRef.current?.focus(), 0);
                  }
                }}
                query={atQuery ?? ''}
                workspaceId={workspaceId ?? ''}
                recentEntities={recentEntities}
                onSelect={handleEntitySelect}
                width={inputWidth ?? undefined}
                commandRef={entityCommandRef}
              />

              <div
                role="textbox"
                aria-multiline="true"
                aria-label="Chat input"
                contentEditable={!isDisabled}
                suppressContentEditableWarning
                data-testid="chat-input"
                ref={editableRef}
                onInput={handleInput}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                className={cn(
                  'min-h-[40px] max-h-[160px] overflow-y-auto resize-none pr-20',
                  'rounded-xl border border-border/60 bg-muted/30',
                  'text-sm',
                  'px-3 py-2',
                  'outline-none focus-visible:ring-1 focus-visible:ring-primary/40 focus-visible:border-primary/40',
                  'transition-colors',
                  'empty:before:content-[attr(data-placeholder)] empty:before:text-muted-foreground/60',
                  isStreaming && 'chat-input-working',
                  isDisabled && 'cursor-not-allowed opacity-50'
                )}
                data-placeholder="Ask anything… or type / for skills"
              />

              {/* Inline toolbar buttons */}
              <div className="absolute bottom-1.5 right-2 flex items-center gap-0.5">
                <RecordButton
                  workspaceId={workspaceId ?? ''}
                  onTranscript={(text, audioUrl) => {
                    // Append committed transcript to the pre-recording text
                    const base = preRecordTextRef.current;
                    onChange(base + (base ? ' ' : '') + text);
                    preRecordTextRef.current = '';
                    setPendingAudioUrl(audioUrl);
                    setTimeout(() => editableRef.current?.focus(), 0);
                  }}
                  onPartialTranscript={(text) => {
                    // Save original text on first partial, then show live preview
                    if (!preRecordTextRef.current && !text) return;
                    if (!preRecordTextRef.current) {
                      preRecordTextRef.current = value;
                    }
                    const base = preRecordTextRef.current;
                    onChange(base + (base ? ' ' : '') + text);
                  }}
                  disabled={isDisabled || isStreaming || !workspaceId}
                />
                <AttachmentButton
                  onAddFile={addFile}
                  disabled={isDisabled || isStreaming}
                  driveConnected={driveStatus?.connected}
                  onConnectDrive={handleConnectDrive}
                  onOpenDrivePicker={() => setDrivePickerOpen(true)}
                />
                {tokenBudgetPercent != null && tokenBudgetPercent > 0 && (
                  <TokenBudgetRing
                    percentage={tokenBudgetPercent}
                    tokensUsed={tokensUsed}
                    tokenBudget={tokenBudget}
                  />
                )}
                <SkillMenu
                  open={skillMenuOpen}
                  onOpenChange={(open) => {
                    setSkillMenuOpen(open);
                    if (!open) {
                      setSlashQuery(null);
                      slashQueryStartOffsetRef.current = null;
                      if (skipFocusOnSkillCloseRef.current) {
                        skipFocusOnSkillCloseRef.current = false;
                      } else {
                        setTimeout(() => editableRef.current?.focus(), 0);
                      }
                    }
                  }}
                  onSelect={handleSkillSelect}
                  onCancel={handleSkillCancel}
                  skills={dynamicSkills}
                  popoverWidth={inputWidth ?? undefined}
                  searchQuery={slashQuery ?? ''}
                  commandRef={skillCommandRef}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setSkillMenuOpen(true)}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span className="sr-only">Open skill menu</span>
                  </Button>
                </SkillMenu>

                <AgentMenu
                  open={agentMenuOpen}
                  onOpenChange={setAgentMenuOpen}
                  onSelect={handleAgentSelect}
                  popoverWidth={inputWidth ?? undefined}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setAgentMenuOpen(true)}
                  >
                    <AtSign className="h-3.5 w-3.5" />
                    <span className="sr-only">Open agent menu</span>
                  </Button>
                </AgentMenu>

                {noteHeadings && noteHeadings.length > 0 && (
                  <SectionMenu
                    open={sectionMenuOpen}
                    onOpenChange={setSectionMenuOpen}
                    onSelect={handleSectionSelect}
                    onCancel={handleSectionCancel}
                    headings={noteHeadings}
                    popoverWidth={inputWidth ?? undefined}
                  >
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                      onClick={() => setSectionMenuOpen(true)}
                    >
                      <Hash className="h-3.5 w-3.5" />
                      <span className="sr-only">Reference note section</span>
                    </Button>
                  </SectionMenu>
                )}

                <SessionResumeMenu
                  open={resumeMenuOpen}
                  onOpenChange={setResumeMenuOpen}
                  sessions={sessions}
                  isLoading={sessionsLoading}
                  onSelect={handleSessionSelect}
                  onSearch={onSearchSessions}
                  popoverWidth={inputWidth ?? undefined}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
                    onClick={() => setResumeMenuOpen(true)}
                  >
                    <History className="h-3.5 w-3.5" />
                    <span className="sr-only">Resume session</span>
                  </Button>
                </SessionResumeMenu>
              </div>
            </div>

            {/* Working indicator when AI is processing */}
            <WorkingIndicator isVisible={isStreaming} />
          </div>
        </div>

        {drivePickerOpen && workspaceId && (
          <DriveFilePicker
            open={drivePickerOpen}
            onClose={() => setDrivePickerOpen(false)}
            workspaceId={workspaceId}
            sessionId={sessionId}
            onImported={(response) => {
              addFromDrive(response);
              setDrivePickerOpen(false);
            }}
          />
        )}
      </>
    );
  }
);

ChatInput.displayName = 'ChatInput';
