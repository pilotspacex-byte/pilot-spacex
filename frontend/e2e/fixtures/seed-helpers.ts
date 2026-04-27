/**
 * seed-helpers.ts — typed accessor for E2E seed entity ids.
 *
 * Phase 94 Plan 03 Task 1 — decouples specs from raw seed values so the
 * suite is resilient to global-setup changes. Specs import
 * `getSeedContext()` and consume strongly-typed ids.
 *
 * The seed file is produced by `global-setup.ts` after the test user +
 * workspace are created. If a particular entity could not be seeded
 * (API unavailable / 4xx), the corresponding field is `null` and specs
 * that need it will skip with a TODO.
 *
 * @see global-setup.ts — populates SEED_PATH
 * @see frontend/src/__tests__/e2e-fixtures/seed-helpers.test.ts — vitest coverage
 */

import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';

export const SEED_PATH = path.join(__dirname, '..', '.auth', 'seed-context.json');

export interface SeedContext {
  workspaceSlug: string;
  workspaceId: string;
  // Topic / Notes
  rootTopicId: string | null;
  childTopicAId: string | null;
  childTopicBId: string | null;
  /** Topic at depth=5 — drop targets here would push to depth=6 → TopicMaxDepthExceededError. */
  deepTopicId: string | null;
  // Tasks
  taskId: string | null;
  // Chat
  /** Pre-existing chat session with a user message + assistant message + applied artifact. */
  chatSessionId: string | null;
  /** First user message inside chatSessionId — seeded with content="seed". */
  messageId?: string | null;
  /** NOTE artifact (Note.id) linked to chatSessionId via source_chat_session_id. */
  artifactId: string | null;
  // Proposals
  /** EditProposal in 'pending' state targeting taskId. Consumed by edit-proposal-accept.spec. */
  pendingProposalId: string | null;
  // Skills
  skillSlug: string | null;
  skillReferenceFilePath: string | null;
}

/**
 * Load the seed context written by global-setup.ts.
 *
 * @throws when SEED_PATH is missing — global-setup must run first.
 */
export function getSeedContext(): SeedContext {
  if (!existsSync(SEED_PATH)) {
    throw new Error(
      `[seed-helpers] Seed context not found at ${SEED_PATH}. ` +
        `Run Playwright (which triggers global-setup) before invoking specs directly.`
    );
  }
  const raw = readFileSync(SEED_PATH, 'utf-8');
  return JSON.parse(raw) as SeedContext;
}

/**
 * Test-only override — injects a custom seed path. Used by vitest tests
 * to point at a tmp file without touching the real e2e/.auth folder.
 */
export function getSeedContextFrom(seedPath: string): SeedContext {
  if (!existsSync(seedPath)) {
    throw new Error(`[seed-helpers] Seed context not found at ${seedPath}.`);
  }
  return JSON.parse(readFileSync(seedPath, 'utf-8')) as SeedContext;
}
