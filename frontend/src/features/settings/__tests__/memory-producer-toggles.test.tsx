import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryProducerToggles } from '../components/memory-producer-toggles';

// Mock the apiClient
const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock('@/services/api', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

// Mock sonner toast
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

const WORKSPACE_ID = '11111111-1111-1111-1111-111111111111';

const MOCK_TELEMETRY = {
  memory: { hit_rate: 0.42, recall_p95_ms: 85.3, total_recalls: 1234 },
  producers: {
    enqueued: { agent_turn: 500, user_correction: 45, pr_review_finding: 120 },
    dropped: { 'agent_turn::opt_out': 3 },
  },
  toggles: {
    agent_turn: true,
    user_correction: true,
    pr_review_finding: true,
    summarizer: false,
  },
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('MemoryProducerToggles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(MOCK_TELEMETRY);
    mockPut.mockResolvedValue({
      agent_turn: false,
      user_correction: true,
      pr_review_finding: true,
      summarizer: false,
    });
  });

  it('renders 4 toggle switches matching API state', async () => {
    render(<MemoryProducerToggles workspaceId={WORKSPACE_ID} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByRole('switch', { name: /record agent turns/i })).toBeInTheDocument();
    });

    expect(screen.getByRole('switch', { name: /record user corrections/i })).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /record pr review findings/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /summarize memory/i })
    ).toBeInTheDocument();

    // First three should be checked (true), summarizer unchecked (false)
    const agentSwitch = screen.getByRole('switch', { name: /record agent turns/i });
    expect(agentSwitch).toHaveAttribute('data-state', 'checked');

    const summarizerSwitch = screen.getByRole('switch', { name: /summarize memory/i });
    expect(summarizerSwitch).toHaveAttribute('data-state', 'unchecked');
  });

  it('toggling fires mutation with correct producer name and enabled value', async () => {
    const user = userEvent.setup();

    render(<MemoryProducerToggles workspaceId={WORKSPACE_ID} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByRole('switch', { name: /record agent turns/i })).toBeInTheDocument();
    });

    const agentSwitch = screen.getByRole('switch', { name: /record agent turns/i });
    await user.click(agentSwitch);

    await waitFor(() => {
      expect(mockPut).toHaveBeenCalledWith(
        `/workspaces/${WORKSPACE_ID}/ai/memory/telemetry/toggles/agent_turn`,
        { enabled: false }
      );
    });
  });

  it('summarizer toggle starts OFF when toggles.summarizer === false', async () => {
    render(<MemoryProducerToggles workspaceId={WORKSPACE_ID} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByRole('switch', { name: /summarize memory/i })).toBeInTheDocument();
    });

    const summarizerSwitch = screen.getByRole('switch', { name: /summarize memory/i });
    expect(summarizerSwitch).toHaveAttribute('data-state', 'unchecked');
  });
});
