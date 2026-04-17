/**
 * ToolPill — v3 "Tools" entry point. Opens a popover listing available tools
 * (currently a placeholder list; replace with a tools store/API when available).
 *
 * Rendered as a sibling of SkillPill/AgentPill in the Gemini composer toolbar.
 */

import { ChevronDown, Wrench, Globe, ImageIcon, Code2 } from 'lucide-react';
import { useState } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Pill } from './Pill';

interface ToolEntry {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const PLACEHOLDER_TOOLS: ToolEntry[] = [
  { id: 'web-search', label: 'Web Search', description: 'Search the open web', icon: Globe },
  { id: 'code', label: 'Code interpreter', description: 'Run and evaluate code', icon: Code2 },
  { id: 'image', label: 'Image generation', description: 'Create images from prompts', icon: ImageIcon },
];

interface ToolPillProps {
  /** Invoked when a tool is selected. When omitted the pill renders a coming-soon row. */
  onSelectTool?: (toolId: string) => void;
  tools?: ToolEntry[];
  label?: string;
  disabled?: boolean;
}

export function ToolPill({
  onSelectTool,
  tools = PLACEHOLDER_TOOLS,
  label = 'Tools',
  disabled,
}: ToolPillProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Pill
          icon={<Wrench className="h-3.5 w-3.5" aria-hidden="true" />}
          label={label}
          trailing={<ChevronDown className="h-3 w-3 opacity-60" aria-hidden="true" />}
          disabled={disabled}
          aria-label="Open tools menu"
          active={open}
        />
      </PopoverTrigger>
      <PopoverContent align="start" side="top" sideOffset={8} className="p-0 w-64">
        <Command>
          <CommandInput placeholder="Search tools…" className="text-sm" />
          <CommandList>
            <CommandEmpty>No tools found.</CommandEmpty>
            <CommandGroup>
              {tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <CommandItem
                    key={tool.id}
                    value={tool.label}
                    onSelect={() => {
                      onSelectTool?.(tool.id);
                      setOpen(false);
                    }}
                    className="flex items-start gap-2 py-2 px-2"
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground" aria-hidden="true" />
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="text-xs font-medium">{tool.label}</span>
                      <span className="text-[11px] text-muted-foreground truncate">
                        {tool.description}
                      </span>
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
}
