/**
 * ActionButtonBar - Horizontal bar of action buttons on issue detail page.
 *
 * Shows max 3 buttons; overflow goes into a "More" dropdown.
 * NOT an observer — receives buttons as props.
 * Source: Phase 17, SKBTN-03
 */

'use client';

import type { LucideIcon } from 'lucide-react';
import {
  Bug,
  Code,
  FileText,
  GitPullRequest,
  MessageSquare,
  MoreHorizontal,
  RefreshCw,
  Rocket,
  Send,
  Settings,
  Shield,
  Sparkles,
  Star,
  Target,
  Wand2,
  Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { SkillActionButton } from '@/services/api/skill-action-buttons';

// ---------------------------------------------------------------------------
// Icon map — curated set of common Lucide icons for action buttons
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, LucideIcon> = {
  Bug,
  Code,
  FileText,
  GitPullRequest,
  MessageSquare,
  RefreshCw,
  Rocket,
  Send,
  Settings,
  Shield,
  Sparkles,
  Star,
  Target,
  Wand2,
  Zap,
};

function resolveLucideIcon(name: string | null): LucideIcon | null {
  if (!name) return null;
  return ICON_MAP[name] ?? Sparkles;
}

// ---------------------------------------------------------------------------
// Stale binding detection
// ---------------------------------------------------------------------------

function isStaleBinding(btn: SkillActionButton): boolean {
  // A button with no binding_id AND no skill_name/tool_name in metadata is stale
  if (btn.binding_id) return false;
  const meta = btn.binding_metadata;
  if (meta && (meta.skill_name || meta.tool_name)) return false;
  return true;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_VISIBLE = 3;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface ActionButtonBarProps {
  buttons: SkillActionButton[];
  onButtonClick: (button: SkillActionButton) => void;
}

export function ActionButtonBar({ buttons, onButtonClick }: ActionButtonBarProps) {
  if (buttons.length === 0) return null;

  const visibleButtons = buttons.slice(0, MAX_VISIBLE);
  const overflowButtons = buttons.slice(MAX_VISIBLE);

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b">
      {visibleButtons.map((btn) => {
        const Icon = resolveLucideIcon(btn.icon);
        const stale = isStaleBinding(btn);

        if (stale) {
          return (
            <Tooltip key={btn.id}>
              <TooltipTrigger asChild>
                <Button variant="secondary" size="sm" disabled>
                  {Icon && <Icon className="mr-1.5 h-3.5 w-3.5" />}
                  {btn.name}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Bound skill/tool is no longer available</TooltipContent>
            </Tooltip>
          );
        }

        return (
          <Button key={btn.id} variant="secondary" size="sm" onClick={() => onButtonClick(btn)}>
            {Icon && <Icon className="mr-1.5 h-3.5 w-3.5" />}
            {btn.name}
          </Button>
        );
      })}

      {overflowButtons.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" size="sm" aria-label="More actions">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {overflowButtons.map((btn) => {
              const Icon = resolveLucideIcon(btn.icon);
              const stale = isStaleBinding(btn);

              return (
                <DropdownMenuItem key={btn.id} onClick={() => onButtonClick(btn)} disabled={stale}>
                  {Icon && <Icon className="mr-2 h-4 w-4" />}
                  {btn.name}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
