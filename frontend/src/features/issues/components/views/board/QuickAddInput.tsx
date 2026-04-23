'use client';

import * as React from 'react';
import { Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickAddInputProps {
  onSubmit: (name: string) => void;
  className?: string;
}

export function QuickAddInput({ onSubmit, className }: QuickAddInputProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [value, setValue] = React.useState('');
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) {
      onSubmit(trimmed);
      setValue('');
    }
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape') {
      setValue('');
      setIsOpen(false);
    }
  };

  React.useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground',
          'hover:bg-accent/50 transition-colors',
          className
        )}
        aria-label="Add new issue"
      >
        <Plus className="size-3.5" />
        <span>New issue</span>
      </button>
    );
  }

  return (
    <input
      ref={inputRef}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={handleSubmit}
      placeholder="Task title..."
      className={cn(
        'w-full rounded-md border bg-background px-2 py-1.5 text-xs',
        'focus:outline-none focus:ring-2 focus:ring-ring',
        className
      )}
      aria-label="New task title"
    />
  );
}
