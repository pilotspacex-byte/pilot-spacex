/**
 * Types and interfaces for CycleStore.
 *
 * Extracted from CycleStore to keep files under 700 lines.
 */
import type { Issue, CycleStatus } from '@/types';

/**
 * Issue display type for cycle board - simplified version
 */
export interface CycleIssue extends Issue {
  storyPoints?: number;
}

/**
 * Filters for cycle list
 */
export interface CycleFilters {
  status?: CycleStatus | 'all';
  search?: string;
}

/**
 * Sort options for cycles
 */
export type SortBy = 'sequence' | 'created_at' | 'start_date';
export type SortOrder = 'asc' | 'desc';
