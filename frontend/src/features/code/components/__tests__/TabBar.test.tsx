/**
 * TabBar smoke tests.
 *
 * Tests:
 * 1. Returns null when FileStore has no open files (progressive disclosure)
 * 2. Renders tab items when FileStore has open files
 * 3. Dirty dot indicator appears for dirty files
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { observable } from 'mobx';

// Mock Radix Popover (heavyweight portal-based component)
vi.mock('@/components/ui/popover', () => ({
  Popover: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popover-content">{children}</div>
  ),
}));

// Mock Radix Tooltip
vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip-content">{children}</div>
  ),
}));

// Mock stores module
const mockFileStore = observable({
  openFiles: new Map(),
  activeFileId: null as string | null,
  get tabOrder() {
    return Array.from(this.openFiles.values())
      .sort((a, b) => a.lastAccessed - b.lastAccessed)
      .map((f) => f.id);
  },
  get activeFile() {
    if (!this.activeFileId) return null;
    return this.openFiles.get(this.activeFileId) ?? null;
  },
  setActiveFile: vi.fn(),
  closeFile: vi.fn(),
});

vi.mock('@/stores/RootStore', () => ({
  useFileStore: () => mockFileStore,
}));

import { TabBar } from '../TabBar';

describe('TabBar', () => {
  beforeEach(() => {
    mockFileStore.openFiles.clear();
    mockFileStore.activeFileId = null;
    vi.clearAllMocks();
  });

  it('renders null when no files are open (progressive disclosure)', () => {
    const { container } = render(<TabBar />);
    expect(container.firstChild).toBeNull();
  });

  it('renders tab items when FileStore has open files', () => {
    mockFileStore.openFiles.set('file-1', {
      id: 'file-1',
      name: 'App.tsx',
      path: 'src/App.tsx',
      language: 'typescript',
      isDirty: false,
      content: 'const x = 1;',
      originalContent: 'const x = 1;',
      lastAccessed: Date.now(),
    });
    mockFileStore.openFiles.set('file-2', {
      id: 'file-2',
      name: 'index.ts',
      path: 'src/index.ts',
      language: 'typescript',
      isDirty: false,
      content: 'export {}',
      originalContent: 'export {}',
      lastAccessed: Date.now() + 1,
    });
    mockFileStore.activeFileId = 'file-1';

    render(<TabBar />);

    expect(screen.getByText('App.tsx')).toBeDefined();
    expect(screen.getByText('index.ts')).toBeDefined();
  });

  it('shows dirty dot indicator for dirty files', () => {
    mockFileStore.openFiles.set('dirty-file', {
      id: 'dirty-file',
      name: 'dirty.ts',
      path: 'dirty.ts',
      language: 'typescript',
      isDirty: true,
      content: 'modified content',
      originalContent: 'original content',
      lastAccessed: Date.now(),
    });
    mockFileStore.activeFileId = 'dirty-file';

    render(<TabBar />);

    // Dirty indicator span should be present
    expect(screen.getByTestId('dirty-indicator')).toBeDefined();
  });

  it('does not show dirty indicator for clean files', () => {
    mockFileStore.openFiles.set('clean-file', {
      id: 'clean-file',
      name: 'clean.ts',
      path: 'clean.ts',
      language: 'typescript',
      isDirty: false,
      content: 'const x = 1;',
      originalContent: 'const x = 1;',
      lastAccessed: Date.now(),
    });
    mockFileStore.activeFileId = 'clean-file';

    render(<TabBar />);

    expect(screen.queryByTestId('dirty-indicator')).toBeNull();
  });
});
