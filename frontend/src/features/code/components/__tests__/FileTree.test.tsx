/**
 * FileTree smoke tests.
 *
 * Tests:
 * 1. Renders without crash with empty artifacts array
 * 2. Renders file nodes when artifacts provided
 * 3. onFileSelect callback fires when a file node is clicked
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { observable } from 'mobx';
import type { Artifact } from '@/types/artifact';

// Mock react-virtuoso — jsdom doesn't measure element sizes needed for virtualization
vi.mock('react-virtuoso', () => ({
  Virtuoso: ({
    totalCount,
    itemContent,
  }: {
    totalCount: number;
    itemContent: (index: number) => React.ReactNode;
  }) => (
    <div data-testid="virtuoso">
      {Array.from({ length: totalCount }, (_, i) => (
        <div key={i}>{itemContent(i)}</div>
      ))}
    </div>
  ),
}));

// Mock ScrollArea
vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

// Mock DropdownMenu
vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => (
    <>{children}</>
  ),
  DropdownMenuContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dropdown-content">{children}</div>
  ),
  DropdownMenuItem: ({
    children,
    onSelect,
    disabled,
  }: {
    children: React.ReactNode;
    onSelect?: () => void;
    disabled?: boolean;
  }) => (
    <button onClick={onSelect} disabled={disabled}>
      {children}
    </button>
  ),
}));

const mockFileStore = observable({
  openFiles: new Map(),
  activeFileId: null as string | null,
  openFile: vi.fn(),
  get tabOrder() {
    return [];
  },
  get activeFile() {
    return null;
  },
});

vi.mock('@/stores/RootStore', () => ({
  useFileStore: () => mockFileStore,
}));

import { FileTree } from '../FileTree';

const makeArtifact = (id: string, filename: string): Artifact => ({
  id,
  filename,
  mimeType: 'text/plain',
  sizeBytes: 100,
  status: 'ready',
  uploaderId: 'user-1',
  projectId: 'project-1',
  workspaceId: 'workspace-1',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
});

describe('FileTree', () => {
  const onFileSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFileStore.openFiles.clear();
  });

  it('renders without crash with empty artifacts array', () => {
    render(
      <FileTree artifacts={[]} onFileSelect={onFileSelect} projectId="project-1" />
    );

    expect(screen.getByText('No files yet')).toBeDefined();
  });

  it('renders file nodes when artifacts are provided', () => {
    const artifacts = [
      makeArtifact('art-1', 'App.tsx'),
      makeArtifact('art-2', 'index.ts'),
    ];

    render(
      <FileTree artifacts={artifacts} onFileSelect={onFileSelect} projectId="project-1" />
    );

    expect(screen.getByText('App.tsx')).toBeDefined();
    expect(screen.getByText('index.ts')).toBeDefined();
  });

  it('calls onFileSelect when a file node is clicked', () => {
    const artifacts = [makeArtifact('art-1', 'App.tsx')];

    render(
      <FileTree artifacts={artifacts} onFileSelect={onFileSelect} projectId="project-1" />
    );

    const fileNode = screen.getByText('App.tsx');
    fireEvent.click(fileNode);

    expect(onFileSelect).toHaveBeenCalledWith(artifacts[0]);
  });

  it('renders a "Files" section header', () => {
    const artifacts = [makeArtifact('art-1', 'main.py')];

    render(
      <FileTree artifacts={artifacts} onFileSelect={onFileSelect} projectId="project-1" />
    );

    expect(screen.getByText('Files')).toBeDefined();
  });
});
