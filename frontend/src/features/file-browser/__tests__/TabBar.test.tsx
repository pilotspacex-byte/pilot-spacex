import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FileStore } from '../stores/FileStore';
import type { OpenFile } from '@/features/editor/types';

// Mock the RootStore useFileStore hook
const mockFileStore = new FileStore();

vi.mock('@/stores/RootStore', () => ({
  useFileStore: () => mockFileStore,
}));

// Must import after mock setup
const { TabBar } = await import('../components/TabBar');

function makeFile(overrides: Partial<OpenFile> & { id: string }): Omit<OpenFile, 'isDirty'> {
  return {
    name: `${overrides.id}.ts`,
    path: `/src/${overrides.id}.ts`,
    source: 'local',
    language: 'typescript',
    content: `// ${overrides.id}`,
    isReadOnly: false,
    ...overrides,
  };
}

describe('TabBar', () => {
  beforeEach(() => {
    mockFileStore.reset();
  });

  it('renders nothing when no tabs are open', () => {
    const { container } = render(<TabBar />);
    expect(container.querySelector('[role="tablist"]')).toBeNull();
  });

  it('renders a tab for each open file', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    mockFileStore.openFile(makeFile({ id: 'f2', name: 'app.tsx' }));

    render(<TabBar />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(2);
    expect(screen.getByText('index.ts')).toBeDefined();
    expect(screen.getByText('app.tsx')).toBeDefined();
  });

  it('active tab has primary bottom border class', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    mockFileStore.openFile(makeFile({ id: 'f2', name: 'app.tsx' }));

    render(<TabBar />);
    const tabs = screen.getAllByRole('tab');
    // f2 should be active (opened last)
    const activeTab = tabs.find((t) => t.getAttribute('aria-selected') === 'true');
    expect(activeTab).toBeDefined();
    expect(activeTab!.className).toContain('border-primary');
    expect(activeTab!.textContent).toContain('app.tsx');
  });

  it('inactive tab has muted foreground text class', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    mockFileStore.openFile(makeFile({ id: 'f2', name: 'app.tsx' }));

    render(<TabBar />);
    const tabs = screen.getAllByRole('tab');
    const inactiveTab = tabs.find((t) => t.getAttribute('aria-selected') === 'false');
    expect(inactiveTab).toBeDefined();
    expect(inactiveTab!.className).toContain('text-muted-foreground');
  });

  it('click on tab calls setActiveFile', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    mockFileStore.openFile(makeFile({ id: 'f2', name: 'app.tsx' }));
    expect(mockFileStore.activeFileId).toBe('f2');

    render(<TabBar />);
    const indexTab = screen.getByText('index.ts').closest('[role="tab"]')!;
    fireEvent.click(indexTab);
    expect(mockFileStore.activeFileId).toBe('f1');
  });

  it('close button removes tab', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    expect(mockFileStore.tabs).toHaveLength(1);

    render(<TabBar />);
    const closeBtn = screen.getByLabelText('Close index.ts');
    fireEvent.click(closeBtn);
    expect(mockFileStore.tabs).toHaveLength(0);
  });

  it('middle-click closes tab via onAuxClick', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    expect(mockFileStore.tabs).toHaveLength(1);

    render(<TabBar />);
    const tab = screen.getByRole('tab');
    // auxclick event with button=1 for middle-click
    const auxEvent = new MouseEvent('auxclick', { button: 1, bubbles: true });
    tab.dispatchEvent(auxEvent);
    expect(mockFileStore.tabs).toHaveLength(0);
  });

  it('dirty indicator dot appears when file isDirty', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    mockFileStore.markDirty('f1');

    const { container } = render(<TabBar />);
    // The dirty dot should appear (a small rounded-full element inside the tab)
    const dot = container.querySelector('.rounded-full.bg-primary');
    expect(dot).not.toBeNull();
  });

  it('has 36px height class', () => {
    mockFileStore.openFile(makeFile({ id: 'f1', name: 'index.ts' }));
    const { container } = render(<TabBar />);
    const bar = container.firstElementChild as HTMLElement;
    expect(bar.className).toContain('h-[36px]');
  });
});
