/**
 * SkillPill — v3 pill-shaped trigger for the existing SkillMenu.
 *
 * Wraps SkillMenu verbatim; only the trigger visual changes from the legacy
 * h-6 ghost icon button to a labeled pill with chevron.
 */

import { ChevronDown, Sparkles } from 'lucide-react';
import type { ComponentProps } from 'react';
import { SkillMenu } from '@/features/ai/ChatView/ChatInput/SkillMenu';
import { Pill } from './Pill';

type SkillMenuProps = ComponentProps<typeof SkillMenu>;

interface SkillPillProps extends Omit<SkillMenuProps, 'children'> {
  /** Open the menu programmatically (kept for parity with legacy ChatInput usage). */
  onTriggerClick?: () => void;
  label?: string;
}

export function SkillPill({ onTriggerClick, label = 'Skills', ...menuProps }: SkillPillProps) {
  return (
    <SkillMenu {...menuProps}>
      <Pill
        icon={<Sparkles className="h-3.5 w-3.5" aria-hidden="true" />}
        label={label}
        trailing={<ChevronDown className="h-3 w-3 opacity-60" aria-hidden="true" />}
        onClick={onTriggerClick}
        aria-label="Open skills menu"
      />
    </SkillMenu>
  );
}
