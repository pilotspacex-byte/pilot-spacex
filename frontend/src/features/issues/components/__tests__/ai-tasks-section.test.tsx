import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AITasksSection } from '../ai-tasks-section';
import type { ContextTask, ContextPrompt } from '@/stores/ai/AIContextStore';

vi.mock('@/stores', () => ({
  useTaskStore: vi.fn(() => ({
    fetchTasks: vi.fn(),
    getTasksForIssue: vi.fn(() => []),
    getCompletedCount: vi.fn(() => 0),
    isDecomposing: false,
    error: null,
    decomposeTasks: vi.fn(),
    reorderTasks: vi.fn(),
    updateTask: vi.fn(),
    updateStatus: vi.fn(),
  })),
  useWorkspaceStore: vi.fn(() => ({
    currentWorkspaceId: 'test-workspace-id',
  })),
}));

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('@/components/ui/checkbox', () => ({
  Checkbox: ({
    checked,
    onCheckedChange,
    'aria-label': ariaLabel,
    ...props
  }: {
    checked?: boolean;
    onCheckedChange?: (checked: boolean) => void;
    'aria-label'?: string;
    [key: string]: unknown;
  }) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={() => onCheckedChange?.(!checked)}
      aria-label={ariaLabel}
      {...props}
    />
  ),
}));

vi.mock('../prompt-block', () => ({
  PromptBlock: ({
    prompt,
    defaultExpanded,
  }: {
    prompt: ContextPrompt;
    defaultExpanded?: boolean;
  }) => (
    <div data-testid={`prompt-${prompt.taskId}`}>
      <span>{prompt.title}</span>
      {defaultExpanded && <span data-testid="expanded" />}
    </div>
  ),
}));

describe('AITasksSection', () => {
  const mockTasks: ContextTask[] = [
    {
      id: 1,
      title: 'Implement authentication',
      estimate: '3 days',
      dependencies: [],
      completed: false,
    },
    {
      id: 2,
      title: 'Add user profile page',
      estimate: '2 days',
      dependencies: [1],
      completed: false,
    },
    {
      id: 3,
      title: 'Create dashboard',
      estimate: '5 days',
      dependencies: [1, 2],
      completed: false,
    },
  ];

  const mockPrompts: ContextPrompt[] = [
    {
      taskId: 1,
      title: 'Authentication Implementation Prompt',
      content: 'Implement JWT authentication with refresh tokens using Supabase Auth...',
    },
    {
      taskId: 2,
      title: 'User Profile Prompt',
      content: 'Create a user profile page with editable fields...',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when tasks and prompts are empty', () => {
    const { container } = render(<AITasksSection tasks={[]} prompts={[]} />);

    expect(container.firstChild).toBeNull();
  });

  it('renders task titles and estimates', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    expect(screen.getByText('Implement authentication')).toBeInTheDocument();
    expect(screen.getByText('Add user profile page')).toBeInTheDocument();
    expect(screen.getByText('Create dashboard')).toBeInTheDocument();

    expect(screen.getByText('3 days')).toBeInTheDocument();
    expect(screen.getByText('2 days')).toBeInTheDocument();
    expect(screen.getByText('5 days')).toBeInTheDocument();
  });

  it('renders dependency text with correct format', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    expect(screen.getByText('Depends on: Task 1')).toBeInTheDocument();
    expect(screen.getByText('Depends on: Task 1, Task 2')).toBeInTheDocument();
  });

  it('toggles checkbox and adds line-through styling when task is checked', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    const firstTaskCheckbox = screen.getByLabelText(/Mark "Implement authentication" as/);
    const firstTaskTitle = screen.getByText('Implement authentication');

    expect(firstTaskCheckbox).not.toBeChecked();
    expect(firstTaskTitle).not.toHaveClass('line-through');
    expect(firstTaskTitle).not.toHaveClass('text-muted-foreground');

    fireEvent.click(firstTaskCheckbox);

    expect(firstTaskCheckbox).toBeChecked();
    expect(firstTaskTitle).toHaveClass('line-through');
    expect(firstTaskTitle).toHaveClass('text-muted-foreground');

    fireEvent.click(firstTaskCheckbox);

    expect(firstTaskCheckbox).not.toBeChecked();
    expect(firstTaskTitle).not.toHaveClass('line-through');
  });

  it('renders prompt blocks with first expanded by default', () => {
    render(<AITasksSection tasks={[]} prompts={mockPrompts} />);

    const firstPrompt = screen.getByTestId('prompt-1');
    const secondPrompt = screen.getByTestId('prompt-2');

    expect(firstPrompt).toBeInTheDocument();
    expect(secondPrompt).toBeInTheDocument();

    expect(screen.getByText('Authentication Implementation Prompt')).toBeInTheDocument();
    expect(screen.getByText('User Profile Prompt')).toBeInTheDocument();

    const expandedIndicators = screen.getAllByTestId('expanded');
    expect(expandedIndicators).toHaveLength(1);
    expect(expandedIndicators[0]).toBeInTheDocument();
  });

  it('renders section heading "Implementation Checklist" when tasks exist', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    expect(screen.getByText('Implementation Checklist')).toBeInTheDocument();
  });

  it('renders section heading "Ready-to-Use Prompts" when prompts exist', () => {
    render(<AITasksSection tasks={[]} prompts={mockPrompts} />);

    expect(screen.getByText('Ready-to-Use Prompts')).toBeInTheDocument();
  });

  it('renders both sections when tasks and prompts are provided', () => {
    render(<AITasksSection tasks={mockTasks} prompts={mockPrompts} />);

    expect(screen.getByText('Implementation Checklist')).toBeInTheDocument();
    expect(screen.getByText('Ready-to-Use Prompts')).toBeInTheDocument();

    expect(screen.getByText('Implement authentication')).toBeInTheDocument();
    expect(screen.getByText('Authentication Implementation Prompt')).toBeInTheDocument();
  });

  it('does not render "Implementation Checklist" when tasks are empty', () => {
    render(<AITasksSection tasks={[]} prompts={mockPrompts} />);

    expect(screen.queryByText('Implementation Checklist')).not.toBeInTheDocument();
  });

  it('does not render "Ready-to-Use Prompts" when prompts are empty', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    expect(screen.queryByText('Ready-to-Use Prompts')).not.toBeInTheDocument();
  });

  it('handles task with no estimate', () => {
    const tasksWithoutEstimate: ContextTask[] = [
      {
        id: 1,
        title: 'Simple task',
        estimate: '',
        dependencies: [],
        completed: false,
      },
    ];

    render(<AITasksSection tasks={tasksWithoutEstimate} prompts={[]} />);

    expect(screen.getByText('Simple task')).toBeInTheDocument();
    expect(screen.queryByText(/days/)).not.toBeInTheDocument();
  });

  it('handles task with no dependencies', () => {
    const taskNoDeps: ContextTask[] = [
      {
        id: 1,
        title: 'Independent task',
        estimate: '1 day',
        dependencies: [],
        completed: false,
      },
    ];

    render(<AITasksSection tasks={taskNoDeps} prompts={[]} />);

    expect(screen.getByText('Independent task')).toBeInTheDocument();
    expect(screen.queryByText(/Depends on:/)).not.toBeInTheDocument();
  });

  it('maintains separate checked state for multiple tasks', () => {
    render(<AITasksSection tasks={mockTasks} prompts={[]} />);

    const task1Checkbox = screen.getByLabelText(/Mark "Implement authentication" as/);
    const task2Checkbox = screen.getByLabelText(/Mark "Add user profile page" as/);
    const task3Checkbox = screen.getByLabelText(/Mark "Create dashboard" as/);

    fireEvent.click(task1Checkbox);

    expect(task1Checkbox).toBeChecked();
    expect(task2Checkbox).not.toBeChecked();
    expect(task3Checkbox).not.toBeChecked();

    fireEvent.click(task3Checkbox);

    expect(task1Checkbox).toBeChecked();
    expect(task2Checkbox).not.toBeChecked();
    expect(task3Checkbox).toBeChecked();

    fireEvent.click(task1Checkbox);

    expect(task1Checkbox).not.toBeChecked();
    expect(task2Checkbox).not.toBeChecked();
    expect(task3Checkbox).toBeChecked();
  });

  it('renders correct aria labels and roles for accessibility', () => {
    render(<AITasksSection tasks={mockTasks} prompts={mockPrompts} />);

    const checklistSection = screen.getByLabelText('Implementation checklist');
    expect(checklistSection).toBeInTheDocument();

    const promptsSection = screen.getByLabelText('Ready-to-use prompts');
    expect(promptsSection).toBeInTheDocument();

    const taskList = screen.getByRole('list');
    expect(taskList).toBeInTheDocument();
  });
});
