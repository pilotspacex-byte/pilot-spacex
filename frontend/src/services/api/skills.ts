/**
 * Skills API client — Phase 91 gallery + detail + reference-file streaming.
 *
 * Endpoints (per Plan 91-01):
 *   GET /skills                       → SkillListResponse → unwrapped to `Skill[]`
 *   GET /skills/{slug}                → SkillDetail
 *   GET /skills/{slug}/files/{path}   → reference file bytes (streamed; the
 *                                       hook layer fetches via apiClient with
 *                                       responseType:'blob' — see
 *                                       useSkillFileBlob, Decision D-91-02-C).
 *
 * Decisions:
 *  - D-91-02-A: snake_case wire format preserved client-side (no transformer).
 *  - D-91-02-B: gallery hook is `useSkillCatalog` to dodge the chat-side
 *    `useSkills` hook collision in `features/ai/ChatView/hooks/useSkills.ts`.
 *  - D-91-02-C: blob fetching uses apiClient (not raw fetch) for auth-
 *    interceptor reuse + RFC 7807 error parity. `fileUrl` here is kept as a
 *    pure URL builder for callers that need an absolute URL (debugging,
 *    `<a href>`, copy-link UI), not for the hook's data path.
 */

import { apiClient } from './client';
import type { Skill, SkillDetail } from '@/types/skill';

/**
 * Encode a multi-segment file path while preserving `/` so FastAPI's `:path`
 * matcher receives the original directory structure (a naive
 * `encodeURIComponent` would collapse slashes to `%2F` and the route would 404).
 *
 * Example: `encodeFilePath("sub dir/file.md") === "sub%20dir/file.md"`.
 */
function encodeFilePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/');
}

/**
 * Resolve the API base URL at call time so tests that toggle
 * `NEXT_PUBLIC_API_URL` via `vi.stubEnv` see the new value without forcing a
 * module re-import. Captured-at-load constants would freeze the env snapshot.
 */
function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
}

export const skillsApi = {
  /**
   * GET /v1/skills — returns the unwrapped skill array (the backend wraps it
   * in `{ skills: [...] }` for forward-compat with pagination).
   */
  async list(): Promise<Skill[]> {
    const res = await apiClient.get<{ skills: Skill[] }>('/skills');
    return res.skills;
  },

  /**
   * GET /v1/skills/{slug} — slug is URL-encoded so accidental special chars
   * cannot break the path. Backend Plan 01 owns path-traversal hardening.
   */
  async get(slug: string): Promise<SkillDetail> {
    return apiClient.get<SkillDetail>(`/skills/${encodeURIComponent(slug)}`);
  },

  /**
   * Build the absolute URL for a skill reference file. Caller fetches the
   * bytes — the peek-drawer integration uses `useSkillFileBlob` (which calls
   * apiClient with `responseType: 'blob'`); other callers (copy-link, debug,
   * external preview) can use this URL directly.
   */
  fileUrl(slug: string, path: string): string {
    return `${getApiBase()}/skills/${encodeURIComponent(slug)}/files/${encodeFilePath(path)}`;
  },
};
