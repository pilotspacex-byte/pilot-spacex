'use client';

/**
 * ThreadedDiscussion - Discussion component for note blocks
 * Nested comments with author, timestamp, and resolve actions
 */
import { useCallback, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Reply,
  Check,
  RotateCcw,
  Sparkles,
  Send,
  MoreHorizontal,
  Trash2,
  Edit2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import type { User } from '@/types';

export interface DiscussionComment {
  id: string;
  content: string;
  author: User;
  createdAt: string;
  updatedAt: string;
  isAIGenerated: boolean;
  parentId?: string;
  replies?: DiscussionComment[];
}

export interface Discussion {
  id: string;
  title: string;
  status: 'open' | 'resolved';
  blockId: string;
  blockText: string;
  comments: DiscussionComment[];
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: User;
}

export interface ThreadedDiscussionProps {
  /** Discussion data */
  discussion: Discussion;
  /** Current user for authoring */
  currentUser: User;
  /** Callback to add comment */
  onAddComment: (content: string, parentId?: string) => Promise<void>;
  /** Callback to resolve discussion */
  onResolve: () => Promise<void>;
  /** Callback to reopen discussion */
  onReopen: () => Promise<void>;
  /** Callback to delete comment */
  onDeleteComment?: (commentId: string) => Promise<void>;
  /** Callback to edit comment */
  onEditComment?: (commentId: string, content: string) => Promise<void>;
}

/**
 * Get user initials for avatar fallback
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Comment input component
 */
function CommentInput({
  placeholder,
  onSubmit,
  autoFocus,
}: {
  placeholder: string;
  onSubmit: (content: string) => Promise<void>;
  autoFocus?: boolean;
}) {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!content.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit(content.trim());
      setContent('');
    } finally {
      setIsSubmitting(false);
    }
  }, [content, isSubmitting, onSubmit]);

  return (
    <div className="flex items-end gap-2">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm',
          'placeholder:text-muted-foreground',
          'focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
          'min-h-[80px]'
        )}
        autoFocus={autoFocus}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            handleSubmit();
          }
        }}
      />
      <Button size="icon" onClick={handleSubmit} disabled={!content.trim() || isSubmitting}>
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
}

/**
 * Single comment component
 */
function CommentItem({
  comment,
  depth = 0,
  currentUserId,
  onReply,
  onDelete,
  onEdit,
}: {
  comment: DiscussionComment;
  depth?: number;
  currentUserId: string;
  onReply: (content: string) => Promise<void>;
  onDelete?: () => Promise<void>;
  onEdit?: (content: string) => Promise<void>;
}) {
  const [isReplying, setIsReplying] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);

  const isOwner = comment.author.id === currentUserId;
  const timeAgo = formatDistanceToNow(new Date(comment.createdAt), { addSuffix: true });
  const wasEdited = comment.updatedAt !== comment.createdAt;

  const handleSaveEdit = useCallback(async () => {
    if (!editContent.trim() || !onEdit) return;
    await onEdit(editContent.trim());
    setIsEditing(false);
  }, [editContent, onEdit]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('group', depth > 0 && 'ml-6 border-l-2 border-border pl-4')}
    >
      <div className="flex items-start gap-3">
        <Avatar className="h-8 w-8">
          <AvatarImage src={comment.author.avatarUrl} alt={comment.author.name} />
          <AvatarFallback>{getInitials(comment.author.name)}</AvatarFallback>
        </Avatar>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-foreground">{comment.author.name}</span>
            {comment.isAIGenerated && (
              <Badge variant="outline" className="text-[10px] gap-1">
                <Sparkles className="h-3 w-3 text-ai" />
                AI
              </Badge>
            )}
            <span className="text-xs text-muted-foreground">{timeAgo}</span>
            {wasEdited && <span className="text-xs text-muted-foreground">(edited)</span>}
          </div>

          {isEditing ? (
            <div className="mt-2 space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className={cn(
                  'w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm',
                  'focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
                  'min-h-[60px]'
                )}
                autoFocus
              />
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={handleSaveEdit}>
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setIsEditing(false);
                    setEditContent(comment.content);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-1 text-sm text-foreground prose prose-sm dark:prose-invert max-w-none">
              {comment.content}
            </div>
          )}

          {!isEditing && (
            <div className="mt-2 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => setIsReplying(!isReplying)}
              >
                <Reply className="mr-1 h-3 w-3" />
                Reply
              </Button>

              {(isOwner || onEdit || onDelete) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon-sm" className="h-7 w-7">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {isOwner && onEdit && (
                      <DropdownMenuItem onClick={() => setIsEditing(true)}>
                        <Edit2 className="mr-2 h-4 w-4" />
                        Edit
                      </DropdownMenuItem>
                    )}
                    {isOwner && onDelete && (
                      <DropdownMenuItem className="text-destructive" onClick={onDelete}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reply input */}
      <AnimatePresence>
        {isReplying && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-3 ml-11 overflow-hidden"
          >
            <CommentInput
              placeholder="Write a reply..."
              onSubmit={async (content) => {
                await onReply(content);
                setIsReplying(false);
              }}
              autoFocus
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nested replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="mt-4 space-y-4">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              depth={depth + 1}
              currentUserId={currentUserId}
              onReply={onReply}
              onDelete={onDelete}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}

/**
 * ThreadedDiscussion component
 */
export const ThreadedDiscussion = observer(function ThreadedDiscussion({
  discussion,
  currentUser,
  onAddComment,
  onResolve,
  onReopen,
  onDeleteComment,
  onEditComment,
}: ThreadedDiscussionProps) {
  const isResolved = discussion.status === 'resolved';

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 border-b border-border p-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-semibold text-foreground truncate">{discussion.title}</h3>
            <Badge variant={isResolved ? 'secondary' : 'default'} className="text-[10px]">
              {isResolved ? 'Resolved' : 'Open'}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">
            &ldquo;{discussion.blockText}&rdquo;
          </p>
        </div>

        <Button
          variant={isResolved ? 'outline' : 'default'}
          size="sm"
          onClick={isResolved ? onReopen : onResolve}
        >
          {isResolved ? (
            <>
              <RotateCcw className="mr-2 h-4 w-4" />
              Reopen
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              Resolve
            </>
          )}
        </Button>
      </div>

      {/* Resolution info */}
      {isResolved && discussion.resolvedBy && discussion.resolvedAt && (
        <div className="flex items-center gap-2 border-b border-border bg-muted/30 px-4 py-2">
          <Check className="h-4 w-4 text-green-500" />
          <span className="text-sm text-muted-foreground">
            Resolved by {discussion.resolvedBy.name}{' '}
            {formatDistanceToNow(new Date(discussion.resolvedAt), { addSuffix: true })}
          </span>
        </div>
      )}

      {/* Comments list */}
      <ScrollArea className="flex-1">
        <div className="space-y-6 p-4">
          <AnimatePresence mode="popLayout">
            {discussion.comments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                currentUserId={currentUser.id}
                onReply={(content) => onAddComment(content, comment.id)}
                onDelete={onDeleteComment ? () => onDeleteComment(comment.id) : undefined}
                onEdit={onEditComment ? (content) => onEditComment(comment.id, content) : undefined}
              />
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      {/* New comment input */}
      <div className="border-t border-border p-4">
        <CommentInput
          placeholder="Add a comment..."
          onSubmit={(content) => onAddComment(content)}
        />
      </div>
    </div>
  );
});

export default ThreadedDiscussion;
