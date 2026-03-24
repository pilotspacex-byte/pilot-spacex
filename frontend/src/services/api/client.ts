import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { toast } from 'sonner';
import { getAuthProviderSync } from '@/services/auth/providers';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

/**
 * RFC 7807 Problem Details for HTTP APIs
 */
export interface ApiProblemDetails {
  type?: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

/**
 * Custom API Error class conforming to RFC 7807 Problem Details
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly type: string;
  public readonly detail?: string;
  public readonly errors?: Array<Record<string, unknown>>;
  public readonly isRetryable: boolean;

  constructor(problem: ApiProblemDetails) {
    super(problem.title);
    this.name = 'ApiError';
    this.status = problem.status;
    this.type = problem.type ?? 'about:blank';
    this.detail = problem.detail;
    this.errors = problem.errors;
    this.isRetryable = this.determineRetryable(problem.status);
  }

  private determineRetryable(status: number): boolean {
    // Server errors (except 501 Not Implemented) are retryable
    // 429 Too Many Requests is retryable after backoff
    return (status >= 500 && status !== 501) || status === 429 || status === 408;
  }

  /** Check if an error (e.g. from TanStack Query) is a 403 Forbidden. */
  static isForbidden(error: unknown): boolean {
    return error instanceof ApiError && error.status === 403;
  }

  static fromAxiosError(error: AxiosError<ApiProblemDetails | { detail?: string }>): ApiError {
    const response = error.response;
    const data = response?.data;

    // Handle RFC 7807 format
    if (data && typeof data === 'object' && 'title' in data) {
      return new ApiError(data as ApiProblemDetails);
    }

    // Handle simple { detail: string | array } format (FastAPI errors)
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
        : String(data.detail);
      return new ApiError({
        status: response?.status ?? 500,
        title: detail,
        detail,
      });
    }

    // Network error or no response
    if (error.code === 'ERR_NETWORK' || !response) {
      return new ApiError({
        status: 0,
        title: 'Network Error',
        detail: 'Unable to connect to the server. Please check your internet connection.',
        type: 'network-error',
      });
    }

    // Fallback
    return new ApiError({
      status: response?.status ?? 500,
      title: error.message || 'Request failed',
      detail: error.message,
    });
  }
}

/**
 * Create and configure the axios instance with interceptors
 */
function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE,
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    withCredentials: true,
  });

  // Request interceptor: Add auth token and workspace context
  instance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      try {
        const token = await getAuthProviderSync().getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch {
        // Silent fail - request will proceed without auth header
        console.warn('Failed to get auth session for API request');
      }

      // Add X-Workspace-Id header from localStorage if not already set.
      // The workspace ID is stored by WorkspaceStore.setCurrentWorkspace().
      if (!config.headers['X-Workspace-Id'] && !config.headers['X-Workspace-ID']) {
        if (typeof window !== 'undefined') {
          const storedWorkspaceId = localStorage.getItem('pilot-space:current-workspace');
          const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
          if (storedWorkspaceId && uuidPattern.test(storedWorkspaceId)) {
            config.headers['X-Workspace-Id'] = storedWorkspaceId;
          }
        }
      }

      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor: Handle errors
  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError<ApiProblemDetails | { detail?: string }>) => {
      const status = error.response?.status;
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retried?: boolean };

      // Handle 401 Unauthorized — attempt token refresh before logout
      if (status === 401 && originalRequest && !originalRequest._retried) {
        originalRequest._retried = true;

        try {
          // getToken() handles silent refresh internally
          const freshToken = await getAuthProviderSync().getToken();
          if (freshToken) {
            originalRequest.headers.Authorization = `Bearer ${freshToken}`;
            return instance(originalRequest);
          }
        } catch {
          // Refresh failed — fall through to logout
        }

        // Token refresh failed or returned null — session is dead
        await getAuthProviderSync()
          .logout()
          .catch(() => undefined);

        if (typeof window !== 'undefined') {
          const currentPath = window.location.pathname + window.location.search;
          if (currentPath !== '/login') {
            sessionStorage.setItem('redirectAfterLogin', currentPath);
          }
          window.location.href = '/login?error=session_expired';
        }

        return Promise.reject(
          new ApiError({
            status: 401,
            title: 'Session Expired',
            detail: 'Your session has expired. Please sign in again.',
          })
        );
      }

      // Handle 429 Too Many Requests - show toast
      if (status === 429) {
        const retryAfter = error.response?.headers['retry-after'];
        const waitTime = retryAfter ? parseInt(retryAfter, 10) : 60;

        toast.error('Rate Limit Exceeded', {
          description: `Too many requests. Please wait ${waitTime} seconds before trying again.`,
          duration: 5000,
        });

        return Promise.reject(
          new ApiError({
            status: 429,
            title: 'Rate Limit Exceeded',
            detail: `Too many requests. Please retry after ${waitTime} seconds.`,
          })
        );
      }

      // Handle 403 Forbidden
      if (status === 403) {
        toast.error('Access Denied', {
          description: 'You do not have permission to perform this action.',
          duration: 4000,
        });
      }

      // Handle 500+ Server errors
      if (status && status >= 500) {
        toast.error('Server Error', {
          description: 'An unexpected error occurred. Our team has been notified.',
          duration: 4000,
        });
      }

      return Promise.reject(ApiError.fromAxiosError(error));
    }
  );

  return instance;
}

// Create the singleton axios instance
const axiosInstance = createApiClient();

/**
 * Typed API client with convenience methods
 *
 * @example
 * // GET request
 * const notes = await apiClient.get<Note[]>('/notes');
 *
 * // POST request
 * const note = await apiClient.post<Note>('/notes', { title: 'New Note' });
 *
 * // PATCH request
 * const updated = await apiClient.patch<Note>('/notes/123', { title: 'Updated' });
 *
 * // DELETE request
 * await apiClient.delete('/notes/123');
 */
export const apiClient = {
  /**
   * GET request
   */
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    axiosInstance.get<T>(url, config).then((res) => res.data),

  /**
   * POST request
   */
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    axiosInstance.post<T>(url, data, config).then((res) => res.data),

  /**
   * PUT request
   */
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    axiosInstance.put<T>(url, data, config).then((res) => res.data),

  /**
   * PATCH request
   */
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    axiosInstance.patch<T>(url, data, config).then((res) => res.data),

  /**
   * DELETE request
   */
  delete: <T = void>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    axiosInstance.delete<T>(url, config).then((res) => res.data),

  /**
   * Raw axios instance for advanced use cases
   */
  instance: axiosInstance,
};

/**
 * Paginated response wrapper
 * Uses 'items' field for backward compatibility with existing API services
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  nextCursor: string | null;
  prevCursor: string | null;
  hasNext: boolean;
  hasPrev: boolean;
  pageSize: number;
}

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  meta?: {
    timestamp: string;
    requestId: string;
  };
}
