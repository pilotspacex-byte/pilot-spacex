/**
 * Contract test: PM Block Type Parity (T-228, 017-M6d)
 *
 * Validates that the frontend's PM_BLOCK_TYPES matches the canonical set
 * defined in specs/contracts/pm-block-types.json.
 *
 * Both backend and frontend must agree on the complete set; divergence breaks
 * the AI tool/editor contract (FR-043, FR-044).
 *
 * Current expected set:
 *   Original 6: decision, form, raci, risk, timeline, dashboard
 *   New 4 (017): sprint-board, dependency-map, capacity-plan, release-notes
 *
 * @module pm-blocks/__tests__/pm-block-contract.test
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import { PM_BLOCK_TYPES } from '../PMBlockExtension';

// ---------------------------------------------------------------------------
// Contract source of truth
// ---------------------------------------------------------------------------

const CONTRACT_PATH = resolve(
  __dirname,
  '../../../../../../../../specs/contracts/pm-block-types.json'
);

interface PMBlockContract {
  block_types: string[];
  coverage: {
    original_6: string[];
    new_4_from_017: string[];
  };
}

function loadContract(): PMBlockContract {
  const raw = readFileSync(CONTRACT_PATH, 'utf-8');
  return JSON.parse(raw) as PMBlockContract;
}

// ---------------------------------------------------------------------------
// Contract tests
// ---------------------------------------------------------------------------

describe('PM Block Type Contract (T-228, FR-043, FR-044)', () => {
  it('contract file is readable', () => {
    expect(() => loadContract()).not.toThrow();
  });

  it('frontend PM_BLOCK_TYPES exactly matches contract', () => {
    const contract = loadContract();
    const contractSet = new Set(contract.block_types);
    const frontendSet = new Set<string>(PM_BLOCK_TYPES);

    const missingFromFrontend = [...contractSet].filter((t) => !frontendSet.has(t));
    const extraInFrontend = [...frontendSet].filter((t) => !contractSet.has(t));

    expect(missingFromFrontend).toEqual([]);
    expect(extraInFrontend).toEqual([]);
  });

  it('original 6 PM block types are always present', () => {
    const contract = loadContract();
    const frontendSet = new Set<string>(PM_BLOCK_TYPES);

    for (const bt of contract.coverage.original_6) {
      expect(frontendSet.has(bt)).toBe(true);
    }
  });

  it('4 new PM block types from Feature 017 are in the contract', () => {
    const contract = loadContract();
    const contractSet = new Set(contract.block_types);

    for (const bt of contract.coverage.new_4_from_017) {
      expect(contractSet.has(bt)).toBe(true);
    }
  });

  it('PM_BLOCK_TYPES contains no duplicates', () => {
    const asArray = Array.from(PM_BLOCK_TYPES);
    const asSet = new Set(asArray);
    expect(asArray.length).toBe(asSet.size);
  });

  it('all PM block type values are non-empty strings', () => {
    for (const bt of PM_BLOCK_TYPES) {
      expect(typeof bt).toBe('string');
      expect(bt.trim().length).toBeGreaterThan(0);
    }
  });

  it('contract version field is present', () => {
    const raw = JSON.parse(readFileSync(CONTRACT_PATH, 'utf-8')) as { version?: string };
    expect(raw.version).toBeDefined();
    expect(typeof raw.version).toBe('string');
  });
});
