/**
 * useSkillGraphData — bridges Plan 91-02's `useSkillCatalog` query with
 * Plan 92-01's pure `buildSkillGraph` helper.
 *
 * Phase 92 Plan 02 Task 1.
 *
 * Memoization contract: `buildSkillGraph` is invoked inside `useMemo` keyed
 * on the catalog's `data` reference identity. Two consecutive renders with
 * the same `data` array reference therefore yield the same `graph` object
 * reference — letting Plan 92-02's downstream layout hook (and React Flow's
 * shallow-equality checks) skip unnecessary work.
 *
 * Returns `graph: null` while the catalog is pending or has errored. The
 * graph view's branching code (`SkillGraphView`) treats `null` as the
 * "show skeleton or error block" signal and avoids mounting React Flow
 * with a partial dataset.
 */
'use client';

import { useMemo } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import type { Skill } from '@/types/skill';
import type { ApiError } from '@/services/api/client';
import { useSkillCatalog } from './useSkillCatalog';
import { buildSkillGraph, type SkillGraphResult } from '../lib/skill-graph';

export interface UseSkillGraphDataResult {
  /** Forwarded TanStack query result so consumers can read pending/error flags + refetch. */
  catalog: UseQueryResult<Skill[], ApiError>;
  /**
   * Bipartite skill→file graph, or `null` while the catalog is pending or
   * in an error state. Memoized on `catalog.data` reference identity.
   */
  graph: SkillGraphResult | null;
}

export function useSkillGraphData(): UseSkillGraphDataResult {
  const catalog = useSkillCatalog();
  const graph = useMemo<SkillGraphResult | null>(() => {
    if (!catalog.data) return null;
    return buildSkillGraph(catalog.data);
  }, [catalog.data]);

  return { catalog, graph };
}
