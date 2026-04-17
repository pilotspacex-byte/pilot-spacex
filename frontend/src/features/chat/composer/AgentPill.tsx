/**
 * AgentPill — v3 pill-shaped trigger for the existing AgentMenu.
 */

import { AtSign, ChevronDown } from 'lucide-react';
import type { ComponentProps } from 'react';
import { AgentMenu } from '@/features/ai/ChatView/ChatInput/AgentMenu';
import { Pill } from './Pill';

type AgentMenuProps = ComponentProps<typeof AgentMenu>;

interface AgentPillProps extends Omit<AgentMenuProps, 'children'> {
  onTriggerClick?: () => void;
  label?: string;
}

export function AgentPill({ onTriggerClick, label = 'Agents', ...menuProps }: AgentPillProps) {
  return (
    <AgentMenu {...menuProps}>
      <Pill
        icon={<AtSign className="h-3.5 w-3.5" aria-hidden="true" />}
        label={label}
        trailing={<ChevronDown className="h-3 w-3 opacity-60" aria-hidden="true" />}
        onClick={onTriggerClick}
        aria-label="Open agents menu"
      />
    </AgentMenu>
  );
}
