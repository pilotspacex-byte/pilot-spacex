/**
 * AgentMenu - Searchable agent selector with keyboard navigation
 * Follows shadcn/ui Command pattern for accessible menus
 */

import { memo, useCallback } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { GitPullRequest, Brain, BookOpen } from 'lucide-react';
import { AGENTS } from '../constants';
import type { AgentDefinition } from '../types';

interface AgentMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (agent: AgentDefinition) => void;
  children: React.ReactNode;
  /** Width in pixels for popover content */
  popoverWidth?: number;
}

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  GitPullRequest,
  Brain,
  BookOpen,
};

export const AgentMenu = memo<AgentMenuProps>(({ open, onOpenChange, onSelect, children, popoverWidth }) => {
  const handleSelect = useCallback(
    (agentName: string) => {
      const agent = AGENTS.find((a) => a.name === agentName);
      if (agent) {
        onSelect(agent);
        onOpenChange(false);
      }
    },
    [onSelect, onOpenChange]
  );

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        className={cn("p-0 w-auto")}
        align="start"
        side="top"
        sideOffset={8}
        style={{ width: popoverWidth ?? 450 }}
      >
        <Command>
          <CommandInput placeholder="Search agents..." />
          <CommandList>
            <CommandEmpty>No agents found.</CommandEmpty>

            <CommandGroup heading="Specialized Agents">
              {AGENTS.map((agent) => {
                const AgentIcon = ICON_MAP[agent.icon] || Brain;

                return (
                  <CommandItem
                    key={agent.name}
                    value={agent.name}
                    onSelect={handleSelect}
                    className="flex items-start gap-3 py-3"
                  >
                    <AgentIcon className="h-5 w-5 shrink-0 mt-0.5 text-primary" />

                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium">@{agent.name}</span>
                      </div>

                      <p className="text-xs text-muted-foreground">{agent.description}</p>

                      <div className="flex flex-wrap gap-1">
                        {agent.capabilities.map((capability) => (
                          <Badge
                            key={capability}
                            variant="secondary"
                            className="text-xs font-normal"
                          >
                            {capability}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
});

AgentMenu.displayName = 'AgentMenu';
