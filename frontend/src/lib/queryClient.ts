import { QueryClient, type QueryClientConfig } from '@tanstack/react-query';

/**
 * Query client configuration for Pilot Space
 *
 * @remarks
 * - staleTime: 5 minutes - Data is considered fresh for 5 minutes
 * - gcTime: 30 minutes - Unused data is garbage collected after 30 minutes
 * - retry: 3 times with exponential backoff - Resilient to transient failures
 * - refetchOnWindowFocus: true - Keep data fresh when user returns to app
 */
const queryClientConfig: QueryClientConfig = {
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes (garbage collection time)
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff: 1s, 2s, 4s, max 30s
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      refetchOnMount: true,
    },
    mutations: {
      retry: 1, // Only retry mutations once
      retryDelay: 1000,
    },
  },
};

/**
 * Create a new QueryClient instance with Pilot Space configuration
 * Use this for creating client-side QueryClient instances
 */
export function createQueryClient(): QueryClient {
  return new QueryClient(queryClientConfig);
}

/**
 * Singleton QueryClient getter for use in providers
 * Creates the client only once on the client side
 */
let browserQueryClient: QueryClient | undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === 'undefined') {
    // Server: always create a new query client
    return createQueryClient();
  }
  // Browser: use singleton pattern
  if (!browserQueryClient) {
    browserQueryClient = createQueryClient();
  }
  return browserQueryClient;
}

/**
 * Query key factory for consistent key generation
 * @example
 * queryKeys.notes.list(workspaceId) -> ['notes', 'list', workspaceId]
 * queryKeys.notes.detail(noteId) -> ['notes', 'detail', noteId]
 */
export const queryKeys = {
  // Notes
  notes: {
    all: ['notes'] as const,
    lists: () => [...queryKeys.notes.all, 'list'] as const,
    list: (workspaceId: string, filters?: Record<string, unknown>) =>
      [...queryKeys.notes.lists(), workspaceId, filters] as const,
    details: () => [...queryKeys.notes.all, 'detail'] as const,
    detail: (noteId: string) => [...queryKeys.notes.details(), noteId] as const,
  },

  // Issues
  issues: {
    all: ['issues'] as const,
    lists: () => [...queryKeys.issues.all, 'list'] as const,
    list: (workspaceId: string, filters?: Record<string, unknown>) =>
      [...queryKeys.issues.lists(), workspaceId, filters] as const,
    details: () => [...queryKeys.issues.all, 'detail'] as const,
    detail: (issueId: string) => [...queryKeys.issues.details(), issueId] as const,
    context: (issueId: string) => [...queryKeys.issues.detail(issueId), 'context'] as const,
  },

  // Workspaces
  workspaces: {
    all: ['workspaces'] as const,
    lists: () => [...queryKeys.workspaces.all, 'list'] as const,
    list: () => [...queryKeys.workspaces.lists()] as const,
    details: () => [...queryKeys.workspaces.all, 'detail'] as const,
    detail: (workspaceId: string) => [...queryKeys.workspaces.details(), workspaceId] as const,
    members: (workspaceId: string) =>
      [...queryKeys.workspaces.detail(workspaceId), 'members'] as const,
  },

  // Projects
  projects: {
    all: ['projects'] as const,
    lists: () => [...queryKeys.projects.all, 'list'] as const,
    list: (workspaceId: string) => [...queryKeys.projects.lists(), workspaceId] as const,
    details: () => [...queryKeys.projects.all, 'detail'] as const,
    detail: (projectId: string) => [...queryKeys.projects.details(), projectId] as const,
  },

  // Cycles
  cycles: {
    all: ['cycles'] as const,
    lists: () => [...queryKeys.cycles.all, 'list'] as const,
    list: (projectId: string) => [...queryKeys.cycles.lists(), projectId] as const,
    details: () => [...queryKeys.cycles.all, 'detail'] as const,
    detail: (cycleId: string) => [...queryKeys.cycles.details(), cycleId] as const,
    active: (projectId: string) => [...queryKeys.cycles.list(projectId), 'active'] as const,
  },

  // Modules
  modules: {
    all: ['modules'] as const,
    lists: () => [...queryKeys.modules.all, 'list'] as const,
    list: (projectId: string) => [...queryKeys.modules.lists(), projectId] as const,
    details: () => [...queryKeys.modules.all, 'detail'] as const,
    detail: (moduleId: string) => [...queryKeys.modules.details(), moduleId] as const,
  },

  // Users
  users: {
    all: ['users'] as const,
    current: () => [...queryKeys.users.all, 'current'] as const,
    profile: (userId: string) => [...queryKeys.users.all, 'profile', userId] as const,
  },

  // AI
  ai: {
    all: ['ai'] as const,
    suggestions: (noteId: string) => [...queryKeys.ai.all, 'suggestions', noteId] as const,
    context: (issueId: string) => [...queryKeys.ai.all, 'context', issueId] as const,
  },

  // Search
  search: {
    all: ['search'] as const,
    results: (query: string, scope?: string) =>
      [...queryKeys.search.all, 'results', query, scope] as const,
  },

  // Homepage Hub (US-19)
  homepage: {
    all: ['homepage'] as const,
    activity: (workspaceId: string) =>
      [...queryKeys.homepage.all, 'activity', workspaceId] as const,
    digest: (workspaceId: string) => [...queryKeys.homepage.all, 'digest', workspaceId] as const,
  },
} as const;
