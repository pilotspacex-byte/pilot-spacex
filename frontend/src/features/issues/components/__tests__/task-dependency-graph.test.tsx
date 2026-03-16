import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TaskDependencyGraph } from '../task-dependency-graph';

// Mock canvas getContext since jsdom doesn't implement it
const mockContext = {
  scale: vi.fn(),
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  fillText: vi.fn(),
  fillStyle: '',
  strokeStyle: '',
  lineWidth: 0,
  font: '',
  textAlign: '' as CanvasTextAlign,
  textBaseline: '' as CanvasTextBaseline,
};

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    mockContext as unknown as CanvasRenderingContext2D
  );
});

const tasksWithDeps = [
  {
    id: 't1',
    title: 'Setup project',
    status: 'done' as const,
    sortOrder: 0,
    dependencyIds: [],
  },
  {
    id: 't2',
    title: 'Build feature',
    status: 'in_progress' as const,
    sortOrder: 1,
    dependencyIds: ['t1'],
  },
  {
    id: 't3',
    title: 'Write tests',
    status: 'todo' as const,
    sortOrder: 2,
    dependencyIds: ['t2'],
  },
];

const tasksWithoutDeps = [
  {
    id: 't1',
    title: 'Task A',
    status: 'todo' as const,
    sortOrder: 0,
    dependencyIds: [],
  },
  {
    id: 't2',
    title: 'Task B',
    status: 'todo' as const,
    sortOrder: 1,
    dependencyIds: [],
  },
];

describe('TaskDependencyGraph', () => {
  it('renders nothing when tasks have no dependencies', () => {
    const { container } = render(<TaskDependencyGraph tasks={tasksWithoutDeps} />);
    expect(container.querySelector('[data-testid="task-dependency-graph"]')).toBeNull();
  });

  it('renders nothing when tasks array is empty', () => {
    const { container } = render(<TaskDependencyGraph tasks={[]} />);
    expect(container.querySelector('[data-testid="task-dependency-graph"]')).toBeNull();
  });

  it('renders canvas when tasks have dependencies', () => {
    render(<TaskDependencyGraph tasks={tasksWithDeps} />);
    const graph = screen.getByTestId('task-dependency-graph');
    expect(graph).toBeDefined();

    const canvas = graph.querySelector('canvas');
    expect(canvas).toBeDefined();
  });

  it('has correct aria-label on canvas', () => {
    render(<TaskDependencyGraph tasks={tasksWithDeps} />);
    const canvas = screen.getByRole('img');
    expect(canvas.getAttribute('aria-label')).toBe('Task dependency graph showing 3 tasks');
  });

  it('renders screen reader text description', () => {
    render(<TaskDependencyGraph tasks={tasksWithDeps} />);
    const srText = screen.getByText(/Task 1: Setup project/);
    expect(srText).toBeDefined();
    expect(srText.className).toContain('sr-only');
  });

  it('renders loading skeleton when isLoading is true', () => {
    render(<TaskDependencyGraph tasks={tasksWithDeps} isLoading={true} />);
    const loading = screen.getByRole('status');
    expect(loading.getAttribute('aria-label')).toBe('Loading dependency graph');
  });

  it('canvas container has correct classes', () => {
    render(<TaskDependencyGraph tasks={tasksWithDeps} />);
    const graph = screen.getByTestId('task-dependency-graph');
    expect(graph.className).toContain('bg-muted/30');
    expect(graph.className).toContain('border');
    expect(graph.className).toContain('rounded-[10px]');
  });

  it('handles single task with dependency gracefully', () => {
    const singleDep = [
      {
        id: 't1',
        title: 'Root',
        status: 'todo' as const,
        sortOrder: 0,
        dependencyIds: [],
      },
      {
        id: 't2',
        title: 'Child',
        status: 'todo' as const,
        sortOrder: 1,
        dependencyIds: ['t1'],
      },
    ];
    render(<TaskDependencyGraph tasks={singleDep} />);
    expect(screen.getByTestId('task-dependency-graph')).toBeDefined();
  });
});
