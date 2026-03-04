'use client';

/**
 * GitHubImplementationSection — Collapsible GitHub activity + implementation
 * plan panel for the issue detail canvas.
 *
 * Combines the GitHub activity area (PRs / commits / branches) from
 * GitHubSection with an inline implementation plan panel sourced from
 * useImplementationPlan.
 *
 * NOT wrapped in observer() — no direct MobX store reads.
 * affectedNodes is an optional prop wired by Unit 12; the section works
 * without it.
 */

import {
  Check,
  Copy,
  ExternalLink,
  GitBranch,
  GitCommit,
  GitPullRequest,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { CollapsibleSection } from './collapsible-section';
import { CreateBranchPopover } from './create-branch-popover';
import { useImplementationPlan } from '../hooks/use-implementation-plan';
import { useCopyFeedback } from '../hooks/use-copy-feedback';
import { getGraphNodeStyle } from '@/features/issues/utils/graph-styles';
import type { IntegrationLink } from '@/types';
import type { GraphNodeDTO } from '@/types/knowledge-graph';

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface GitHubImplementationSectionProps {
  // GitHub activity (same as GitHubSection props)
  pullRequests: IntegrationLink[];
  commits: IntegrationLink[];
  branches: IntegrationLink[];
  isLoading?: boolean;
  integrationId?: string;
  workspaceId?: string;
  issueId?: string;
  issueIdentifier?: string;
  // Implementation panel
  affectedNodes?: GraphNodeDTO[];
  onAffectedNodeClick?: (nodeId: string) => void;
  // Plan generation
  isGeneratingPlan?: boolean;
  onGeneratePlan?: () => void;
}

// ---------------------------------------------------------------------------
// Styling constants (mirrors github-section.tsx)
// ---------------------------------------------------------------------------

const PR_STATE: Record<string, string> = {
  open: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  merged: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  closed: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

const LINK_CLS =
  'group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';
const EXT_ICO = 'size-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-50';

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GitHubImplementationSection({
  pullRequests,
  commits,
  branches,
  isLoading = false,
  integrationId,
  workspaceId,
  issueId,
  issueIdentifier,
  affectedNodes,
  onAffectedNodeClick,
  isGeneratingPlan = false,
  onGeneratePlan,
}: GitHubImplementationSectionProps) {
  const total = pullRequests.length + commits.length + branches.length;
  const showCreateBranch = branches.length === 0 && !isLoading;
  const canCreateBranch = !!(integrationId && workspaceId && issueId);

  const { data: implementContext, isLoading: isPlanLoading } = useImplementationPlan(
    workspaceId ?? '',
    issueId ?? ''
  );

  const hasPlan = !isPlanLoading && !!implementContext;

  return (
    <CollapsibleSection
      title="GitHub & Implementation"
      icon={<GitBranch className="size-3.5" />}
      defaultOpen={total > 0 || hasPlan}
      count={total > 0 ? total : undefined}
    >
      {/* ------------------------------------------------------------------ */}
      {/* GitHub Activity Area                                                */}
      {/* ------------------------------------------------------------------ */}
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-2 px-2 py-1.5">
              <Skeleton className="size-4 rounded-full shrink-0" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="ml-auto h-4 w-12 rounded-full" />
            </div>
          ))}
        </div>
      ) : total === 0 ? (
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <GitBranch className="size-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No linked GitHub activity</p>
          {showCreateBranch && (
            <div className="flex flex-wrap gap-2">
              <CreateBranchAction
                canCreate={canCreateBranch}
                integrationId={integrationId}
                workspaceId={workspaceId}
                issueId={issueId}
              />
              <GeneratePlanAction
                isGeneratingPlan={isGeneratingPlan}
                onGeneratePlan={onGeneratePlan}
              />
            </div>
          )}
        </div>
      ) : (
        <div>
          {pullRequests.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Pull Requests</p>
              <ul role="list" aria-label="Linked pull requests">
                {pullRequests.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitPullRequest className="size-4 shrink-0 text-muted-foreground" />
                      {link.prNumber != null && (
                        <span className="shrink-0 font-mono text-xs text-muted-foreground">
                          #{link.prNumber}
                        </span>
                      )}
                      <span className="truncate">
                        {link.prTitle ?? link.title ?? link.externalId}
                      </span>
                      {link.prStatus && (
                        <span
                          className={cn(
                            'ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                            PR_STATE[link.prStatus]
                          )}
                        >
                          {link.prStatus.charAt(0).toUpperCase() + link.prStatus.slice(1)}
                        </span>
                      )}
                      <ExternalLink className={cn(EXT_ICO, !link.prStatus && 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}

          {pullRequests.length > 0 && commits.length > 0 && <hr className="border-border my-2" />}

          {commits.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Recent Commits</p>
              <ul role="list" aria-label="Linked commits">
                {commits.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitCommit className="size-4 shrink-0 text-muted-foreground" />
                      <span className="truncate">{link.title ?? link.externalId}</span>
                      {link.authorName && (
                        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                          {link.authorName}
                        </span>
                      )}
                      <ExternalLink className={cn(EXT_ICO, !link.authorName && 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}

          {(pullRequests.length > 0 || commits.length > 0) && branches.length > 0 && (
            <hr className="border-border my-2" />
          )}

          {branches.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Branches</p>
              <ul role="list" aria-label="Linked branches">
                {branches.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitBranch className="size-4 shrink-0 text-muted-foreground" />
                      <span className="truncate font-mono text-xs">{link.externalId}</span>
                      <ExternalLink className={cn(EXT_ICO, 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}

          {showCreateBranch && (
            <div className="mt-3 px-2 flex flex-wrap gap-2">
              <CreateBranchAction
                canCreate={canCreateBranch}
                integrationId={integrationId}
                workspaceId={workspaceId}
                issueId={issueId}
              />
              <GeneratePlanAction
                isGeneratingPlan={isGeneratingPlan}
                onGeneratePlan={onGeneratePlan}
              />
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Implementation Plan Panel (conditional)                             */}
      {/* ------------------------------------------------------------------ */}
      {isPlanLoading && (
        <div className="mt-3 flex items-center gap-2 px-2 py-2">
          <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Loading implementation plan…</span>
        </div>
      )}

      {hasPlan && implementContext && (
        <ImplementationPlanPanel
          implementContext={implementContext}
          issueIdentifier={issueIdentifier ?? ''}
          affectedNodes={affectedNodes}
          onAffectedNodeClick={onAffectedNodeClick}
          isGeneratingPlan={isGeneratingPlan}
          onGeneratePlan={onGeneratePlan}
        />
      )}

      {!isPlanLoading && !hasPlan && total > 0 && (
        <div className="mt-3 px-2">
          <GeneratePlanAction isGeneratingPlan={isGeneratingPlan} onGeneratePlan={onGeneratePlan} />
        </div>
      )}
    </CollapsibleSection>
  );
}

// ---------------------------------------------------------------------------
// ImplementationPlanPanel — rendered when implementContext data is available
// ---------------------------------------------------------------------------

interface ImplementContextShape {
  suggestedBranch?: string;
  aiContext?: {
    tasksChecklist?: string[];
  };
}

interface ImplementationPlanPanelProps {
  implementContext: ImplementContextShape;
  issueIdentifier: string;
  affectedNodes?: GraphNodeDTO[];
  onAffectedNodeClick?: (nodeId: string) => void;
  isGeneratingPlan?: boolean;
  onGeneratePlan?: () => void;
}

function ImplementationPlanPanel({
  implementContext,
  issueIdentifier,
  affectedNodes,
  onAffectedNodeClick,
  isGeneratingPlan = false,
  onGeneratePlan,
}: ImplementationPlanPanelProps) {
  const { copied: copiedInteractive, handleCopy: handleCopyInteractive } = useCopyFeedback();
  const { copied: copiedOneshot, handleCopy: handleCopyOneshot } = useCopyFeedback();

  const interactiveCmd = `pilot implement ${issueIdentifier}`;
  const oneshotCmd = `pilot implement ${issueIdentifier} --oneshot`;

  const tasks = implementContext.aiContext?.tasksChecklist ?? [];

  return (
    <div
      className="mt-3 border-t border-border pt-3 space-y-3"
      data-testid="implementation-plan-panel"
    >
      {/* Branch name */}
      {implementContext.suggestedBranch && (
        <div>
          <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Branch</p>
          <code className="block mx-2 rounded bg-muted px-2 py-1 font-mono text-xs truncate">
            {implementContext.suggestedBranch}
          </code>
        </div>
      )}

      {/* Task checklist */}
      {tasks.length > 0 && (
        <div>
          <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Tasks</p>
          <ul
            className="space-y-1 px-2"
            aria-label="Implementation tasks"
            data-testid="task-checklist"
          >
            {tasks.map((task, idx) => (
              <li key={idx} className="flex items-start gap-2 py-0.5">
                <Checkbox
                  id={`task-${idx}`}
                  disabled
                  className="mt-0.5 shrink-0"
                  aria-label={task}
                />
                <label
                  htmlFor={`task-${idx}`}
                  className="text-xs text-foreground leading-snug cursor-default"
                >
                  {task}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* CLI commands */}
      {issueIdentifier && (
        <div>
          <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">CLI Commands</p>
          <div className="px-2 space-y-1.5">
            <CommandRow
              label="Interactive"
              cmd={interactiveCmd}
              isCopied={copiedInteractive}
              onCopy={() =>
                void handleCopyInteractive(() =>
                  navigator.clipboard.writeText(interactiveCmd).then(() => true)
                )
              }
            />
            <CommandRow
              label="Oneshot (CI)"
              cmd={oneshotCmd}
              isCopied={copiedOneshot}
              onCopy={() =>
                void handleCopyOneshot(() =>
                  navigator.clipboard.writeText(oneshotCmd).then(() => true)
                )
              }
            />
          </div>
        </div>
      )}

      {/* Affected graph nodes */}
      {affectedNodes && affectedNodes.length > 0 && (
        <div>
          <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">
            Affected Graph Nodes ({affectedNodes.length})
          </p>
          <ul className="px-2 space-y-1" aria-label="Affected graph nodes">
            {affectedNodes.map((node) => {
              const style = getGraphNodeStyle(node.nodeType);
              return (
                <li key={node.id}>
                  <button
                    type="button"
                    onClick={() => onAffectedNodeClick?.(node.id)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-xs',
                      'transition-colors hover:bg-accent',
                      'focus-visible:outline-none focus-visible:ring-2',
                      'focus-visible:ring-ring focus-visible:ring-offset-2'
                    )}
                    aria-label={`Open ${node.label} in knowledge graph`}
                    data-testid={`node-chip-${node.id}`}
                  >
                    <span
                      className={cn('size-2 shrink-0 rounded-full', style.tailwind)}
                      aria-hidden="true"
                    />
                    <span className="truncate text-foreground">{node.label}</span>
                    <span className="ml-auto shrink-0 rounded bg-muted px-1 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {style.abbr}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Generate / Regenerate plan button */}
      <div className="px-2">
        <GeneratePlanAction
          isGeneratingPlan={isGeneratingPlan}
          onGeneratePlan={onGeneratePlan}
          isRegenerate
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommandRow — single CLI command with copy button
// ---------------------------------------------------------------------------

interface CommandRowProps {
  label: string;
  cmd: string;
  isCopied: boolean;
  onCopy: () => void;
}

function CommandRow({ label, cmd, isCopied, onCopy }: CommandRowProps) {
  return (
    <div>
      <p className="mb-0.5 text-[11px] text-muted-foreground">{label}</p>
      <div className="flex items-center gap-2 rounded border bg-muted px-2 py-1">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs">{cmd}</code>
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label={`Copy ${label} command`}
          className="h-5 w-5 shrink-0"
          onClick={onCopy}
          data-testid={`copy-btn-${label.toLowerCase().replace(/\s+/g, '-')}`}
        >
          {isCopied ? <Check className="size-3 text-green-600" /> : <Copy className="size-3" />}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CreateBranchAction — renders CreateBranchPopover or disabled button
// ---------------------------------------------------------------------------

interface CreateBranchActionProps {
  canCreate: boolean;
  integrationId?: string;
  workspaceId?: string;
  issueId?: string;
}

function CreateBranchAction({
  canCreate,
  integrationId,
  workspaceId,
  issueId,
}: CreateBranchActionProps) {
  if (canCreate) {
    return (
      <CreateBranchPopover
        integrationId={integrationId!}
        workspaceId={workspaceId!}
        issueId={issueId!}
      />
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="outline" size="sm" disabled aria-label="Create GitHub branch">
          <GitBranch className="size-3.5" />
          Create branch
        </Button>
      </TooltipTrigger>
      <TooltipContent>Connect GitHub first</TooltipContent>
    </Tooltip>
  );
}

// ---------------------------------------------------------------------------
// GeneratePlanAction — renders Generate Plan / Regenerate button
// ---------------------------------------------------------------------------

interface GeneratePlanActionProps {
  isGeneratingPlan?: boolean;
  onGeneratePlan?: () => void;
  isRegenerate?: boolean;
}

function GeneratePlanAction({
  isGeneratingPlan = false,
  onGeneratePlan,
  isRegenerate = false,
}: GeneratePlanActionProps) {
  const label = isRegenerate ? 'Regenerate plan' : 'Generate plan';

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={isGeneratingPlan || !onGeneratePlan}
      aria-label={label}
      onClick={onGeneratePlan}
      data-testid="generate-plan-btn"
    >
      {isGeneratingPlan ? (
        <Loader2 className="size-3.5 animate-spin" />
      ) : (
        <Sparkles className="size-3.5" />
      )}
      {isGeneratingPlan ? 'Generating…' : label}
    </Button>
  );
}
