/**
 * ChatInput - Compact auto-resizing textarea with skill/agent menus
 * Follows shadcn/ui AI prompt input component pattern
 */

import { useCallback, useState, useRef, useEffect, KeyboardEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { toast } from 'sonner';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Sparkles, AtSign, History } from 'lucide-react';
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
import { SessionResumeMenu, type SessionSummary } from './SessionResumeMenu';
import { WorkingIndicator } from './WorkingIndicator';
import { useAttachments } from '../hooks/useAttachments';
import { useDriveStatus } from '../hooks/useDriveStatus';
import { AttachmentButton } from './AttachmentButton';
import { DriveFilePicker } from './DriveFilePicker';
import { attachmentsApi } from '@/services/api/attachments';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (attachmentIds: string[]) => void;
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
  /** Sessions available for \resume command */
  sessions?: SessionSummary[];
  /** Loading state for sessions */
  sessionsLoading?: boolean;
  /** Callback when a session is selected from \resume menu */
  onSelectSession?: (sessionId: string) => void;
  /** Callback when session search is performed */
  onSearchSessions?: (query: string) => void;
  /** Callback when user requests a new session */
  onNewSession?: () => void;
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
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const inputContainerRef = useRef<HTMLDivElement>(null);
    const [skillMenuOpen, setSkillMenuOpen] = useState(false);
    const [agentMenuOpen, setAgentMenuOpen] = useState(false);
    const [resumeMenuOpen, setResumeMenuOpen] = useState(false);
    const [inputWidth, setInputWidth] = useState<number | null>(null);

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

    // Auto-focus textarea when requested
    useEffect(() => {
      if (autoFocus && textareaRef.current) {
        textareaRef.current.focus();
      }
    }, [autoFocus]);

    // Auto-resize textarea
    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
      }
    }, [value]);

    // Detect \skill trigger
    useEffect(() => {
      const lastChar = value.slice(-1);
      const beforeLastChar = value.slice(-2, -1);

      if (lastChar === '\\' && (beforeLastChar === '' || beforeLastChar === ' ')) {
        setSkillMenuOpen(true);
      }
    }, [value]);

    // Detect @agent trigger
    useEffect(() => {
      const lastChar = value.slice(-1);
      const beforeLastChar = value.slice(-2, -1);

      if (lastChar === '@' && (beforeLastChar === '' || beforeLastChar === ' ')) {
        setAgentMenuOpen(true);
      }
    }, [value]);

    // Detect \resume trigger
    useEffect(() => {
      // Check if value ends with \resume (with optional space before)
      if (value.match(/(?:^|\s)\\resume$/)) {
        setResumeMenuOpen(true);
      }
    }, [value]);

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
        // Special handling for \resume - open session picker instead
        if (skill.name === 'resume') {
          const newValue = value.replace(/\\$/, '');
          onChange(newValue);
          setResumeMenuOpen(true);
          return;
        }
        // Special handling for \new - start fresh session
        if (skill.name === 'new') {
          const newValue = value.replace(/\\$/, '');
          onChange(newValue);
          onNewSession?.();
          textareaRef.current?.focus();
          return;
        }
        const newValue = value.replace(/\\$/, `\\${skill.name} `);
        onChange(newValue);
        textareaRef.current?.focus();
      },
      [value, onChange, onNewSession]
    );

    const handleAgentSelect = useCallback(
      (agent: AgentDefinition) => {
        const newValue = value.replace(/@$/, `@${agent.name} `);
        onChange(newValue);
        textareaRef.current?.focus();
      },
      [value, onChange]
    );

    const handleSessionSelect = useCallback(
      (sessionId: string) => {
        // Remove \resume from input
        const newValue = value.replace(/\\resume$/, '').trim();
        onChange(newValue);
        onSelectSession?.(sessionId);
        setResumeMenuOpen(false);
        textareaRef.current?.focus();
      },
      [value, onChange, onSelectSession]
    );

    const handleSkillCancel = useCallback(() => {
      textareaRef.current?.focus();
    }, []);

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (
          e.key === 'Enter' &&
          !e.shiftKey &&
          !skillMenuOpen &&
          !agentMenuOpen &&
          !resumeMenuOpen
        ) {
          e.preventDefault();
          if (value.trim() && !isStreaming && !isDisabled) {
            onSubmit(attachmentIds);
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
        resumeMenuOpen,
        onSubmit,
        attachmentIds,
        reset,
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

            {/* Input area - single container with inline toolbar */}
            <div className="relative" ref={inputContainerRef}>
              <Textarea
                data-testid="chat-input"
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything… or type \ for skills"
                disabled={isDisabled}
                className={cn(
                  'min-h-[40px] max-h-[160px] resize-none pr-20',
                  'rounded-xl border-border/60 bg-muted/30',
                  'text-sm placeholder:text-muted-foreground/60',
                  'focus-visible:ring-1 focus-visible:ring-primary/40 focus-visible:border-primary/40',
                  'transition-colors',
                  isStreaming && 'chat-input-working'
                )}
                rows={1}
              />

              {/* Inline toolbar buttons */}
              <div className="absolute bottom-1.5 right-2 flex items-center gap-0.5">
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
                  onOpenChange={setSkillMenuOpen}
                  onSelect={handleSkillSelect}
                  onCancel={handleSkillCancel}
                  skills={dynamicSkills}
                  popoverWidth={inputWidth ?? undefined}
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
