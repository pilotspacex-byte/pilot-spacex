/**
 * ChatInput - Auto-resizing textarea with skill/agent menus
 * Follows shadcn/ui AI prompt input component pattern
 */

import { useCallback, useState, useRef, useEffect, KeyboardEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Square, Sparkles, AtSign } from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  NoteContext,
  IssueContext,
  ProjectContext,
  SkillDefinition,
  AgentDefinition,
} from '../types';
import { ContextIndicator } from './ContextIndicator';
import { SkillMenu } from './SkillMenu';
import { AgentMenu } from './AgentMenu';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming?: boolean;
  isDisabled?: boolean;
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  onAbort?: () => void;
  className?: string;
}

export const ChatInput = observer<ChatInputProps>(
  ({
    value,
    onChange,
    onSubmit,
    isStreaming = false,
    isDisabled = false,
    noteContext,
    issueContext,
    projectContext,
    onClearNoteContext,
    onClearIssueContext,
    onClearProjectContext,
    onAbort,
    className,
  }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [skillMenuOpen, setSkillMenuOpen] = useState(false);
    const [agentMenuOpen, setAgentMenuOpen] = useState(false);

    // Auto-resize textarea
    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
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

    const handleSkillSelect = useCallback(
      (skill: SkillDefinition) => {
        // Replace \\ with \skill-name
        const newValue = value.replace(/\\$/, `\\${skill.name} `);
        onChange(newValue);
        textareaRef.current?.focus();
      },
      [value, onChange]
    );

    const handleAgentSelect = useCallback(
      (agent: AgentDefinition) => {
        // Replace @ with @agent-name
        const newValue = value.replace(/@$/, `@${agent.name} `);
        onChange(newValue);
        textareaRef.current?.focus();
      },
      [value, onChange]
    );

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLTextAreaElement>) => {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey && !skillMenuOpen && !agentMenuOpen) {
          e.preventDefault();
          if (value.trim() && !isStreaming && !isDisabled) {
            onSubmit();
          }
        }
      },
      [value, isStreaming, isDisabled, skillMenuOpen, agentMenuOpen, onSubmit]
    );

    const handleSubmitClick = useCallback(() => {
      if (value.trim() && !isStreaming && !isDisabled) {
        onSubmit();
      }
    }, [value, isStreaming, isDisabled, onSubmit]);

    const canSubmit = value.trim().length > 0 && !isStreaming && !isDisabled;

    return (
      <div className={cn('border-t bg-background', className)}>
        <div className="p-4 space-y-3">
          {/* Context indicator */}
          <ContextIndicator
            noteContext={noteContext}
            issueContext={issueContext}
            projectContext={projectContext}
            onClearNoteContext={onClearNoteContext}
            onClearIssueContext={onClearIssueContext}
            onClearProjectContext={onClearProjectContext}
          />

          {/* Input area */}
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <Textarea
                data-testid="chat-input"
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me anything... (use \skill or @agent)"
                disabled={isDisabled}
                className="min-h-[60px] max-h-[200px] resize-none pr-20"
                rows={2}
              />

              {/* Toolbar buttons */}
              <div className="absolute bottom-2 right-2 flex items-center gap-1">
                <SkillMenu
                  open={skillMenuOpen}
                  onOpenChange={setSkillMenuOpen}
                  onSelect={handleSkillSelect}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setSkillMenuOpen(true)}
                  >
                    <Sparkles className="h-4 w-4" />
                    <span className="sr-only">Open skill menu</span>
                  </Button>
                </SkillMenu>

                <AgentMenu
                  open={agentMenuOpen}
                  onOpenChange={setAgentMenuOpen}
                  onSelect={handleAgentSelect}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setAgentMenuOpen(true)}
                  >
                    <AtSign className="h-4 w-4" />
                    <span className="sr-only">Open agent menu</span>
                  </Button>
                </AgentMenu>
              </div>
            </div>

            {/* Submit/Abort button */}
            {isStreaming ? (
              <Button
                data-testid="abort-button"
                type="button"
                variant="destructive"
                size="icon"
                onClick={onAbort}
                className="shrink-0"
              >
                <Square className="h-4 w-4" />
                <span className="sr-only">Stop streaming</span>
              </Button>
            ) : (
              <Button
                data-testid="send-button"
                type="button"
                size="icon"
                onClick={handleSubmitClick}
                disabled={!canSubmit}
                className="shrink-0"
              >
                <Send className="h-4 w-4" />
                <span className="sr-only">Send message</span>
              </Button>
            )}
          </div>

          {/* Helper text */}
          <p className="text-xs text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">Enter</kbd> to
            send,{' '}
            <kbd className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">Shift + Enter</kbd>{' '}
            for new line
          </p>
        </div>
      </div>
    );
  }
);

ChatInput.displayName = 'ChatInput';
