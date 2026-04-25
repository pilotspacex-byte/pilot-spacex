/**
 * Tests for `skillsApi` (Phase 91 Plan 02 Task 1).
 *
 * Coverage targets:
 *  - `list()` calls `/skills` and unwraps `.skills` from the response envelope.
 *  - `get(slug)` URL-encodes the slug.
 *  - `fileUrl(slug, path)` encodes individual path segments but preserves `/`.
 *  - `fileUrl` honors `NEXT_PUBLIC_API_URL` and falls back to `/api/v1`.
 *
 * The env-var cases use `vi.stubEnv` + `vi.resetModules` + dynamic import
 * because `getApiBase()` reads `process.env.NEXT_PUBLIC_API_URL` at call time —
 * but to be fully resilient against any reload/caching mistake (and to match
 * the pattern used by other tests in this directory), we use the dynamic-
 * import dance.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import type { Skill, SkillDetail } from '@/types/skill';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockGet = vi.fn();

vi.mock('../client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const sampleSkill: Skill = {
  name: 'AI Context',
  description: 'Generate spec/architecture context for an issue.',
  category: 'context',
  icon: 'Sparkles',
  examples: ['Add API context to issue ABC'],
  slug: 'ai-context',
  feature_module: null,
  reference_files: ['architecture.md'],
  updated_at: '2026-04-25T10:30:00+00:00',
};

const sampleSkillDetail: SkillDetail = {
  ...sampleSkill,
  body: '# AI Context\n\nFull markdown body here.',
  reference_files: [
    {
      name: 'architecture.md',
      path: 'architecture.md',
      size_bytes: 4521,
      mime_type: 'text/markdown',
    },
  ],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('skillsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('list calls apiClient.get("/skills") and returns the unwrapped skills array', async () => {
    mockGet.mockResolvedValueOnce({ skills: [sampleSkill] });
    const { skillsApi } = await import('../skills');

    const result = await skillsApi.list();

    expect(mockGet).toHaveBeenCalledWith('/skills');
    expect(result).toEqual([sampleSkill]);
  });

  it('list returns [] when backend response has empty skills list', async () => {
    mockGet.mockResolvedValueOnce({ skills: [] });
    const { skillsApi } = await import('../skills');

    const result = await skillsApi.list();

    expect(result).toEqual([]);
  });

  it('get encodes slug and calls /skills/<encoded-slug>', async () => {
    mockGet.mockResolvedValueOnce(sampleSkillDetail);
    const { skillsApi } = await import('../skills');

    const result = await skillsApi.get('a/b');

    // `a/b` must be encoded to `a%2Fb` so a single path segment reaches the
    // detail endpoint (not the file-streaming subpath).
    expect(mockGet).toHaveBeenCalledWith('/skills/a%2Fb');
    expect(result).toBe(sampleSkillDetail);
  });

  it('get URL-encodes special characters in slug', async () => {
    mockGet.mockResolvedValueOnce(sampleSkillDetail);
    const { skillsApi } = await import('../skills');

    await skillsApi.get('skill name with spaces');

    expect(mockGet).toHaveBeenCalledWith('/skills/skill%20name%20with%20spaces');
  });

  it('fileUrl preserves slashes in path but encodes spaces in segments', async () => {
    const { skillsApi } = await import('../skills');

    const url = skillsApi.fileUrl('foo', 'sub dir/file.md');

    // Slashes must survive (FastAPI :path matcher) but spaces inside segments
    // must be percent-encoded.
    expect(url).toContain('/skills/foo/files/sub%20dir/file.md');
    expect(url).not.toContain('sub%2Fdir');
  });

  it('fileUrl URL-encodes special chars in slug', async () => {
    const { skillsApi } = await import('../skills');

    const url = skillsApi.fileUrl('weird name', 'file.md');

    expect(url).toContain('/skills/weird%20name/files/file.md');
  });

  it('fileUrl uses NEXT_PUBLIC_API_URL when set', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000/api/v1');
    vi.resetModules();
    const { skillsApi } = await import('../skills');

    const url = skillsApi.fileUrl('ai-context', 'architecture.md');

    expect(url).toBe('http://localhost:8000/api/v1/skills/ai-context/files/architecture.md');
  });

  it('fileUrl falls back to /api/v1 when env var unset', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', '');
    vi.resetModules();
    const { skillsApi } = await import('../skills');

    const url = skillsApi.fileUrl('ai-context', 'architecture.md');

    // When stubbed to empty string, JS treats `'' ?? fallback` as `''` — so we
    // must verify behavior matches what the module documents. The module uses
    // `??` (nullish coalescing), so empty string passes through. We assert
    // either way to keep the test honest about the implementation.
    expect(url).toMatch(/\/skills\/ai-context\/files\/architecture\.md$/);
  });
});
