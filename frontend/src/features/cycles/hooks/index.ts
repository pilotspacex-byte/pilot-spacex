/**
 * Cycle hooks index.
 *
 * T169: TanStack Query hooks for cycles feature.
 */

// List hooks
export {
  useCycles,
  useInfiniteCycles,
  usePrefetchCycles,
  cyclesKeys,
  selectAllCycles,
  selectCyclesByStatus,
  selectActiveCycle,
  CYCLES_QUERY_KEY,
  type UseCyclesOptions,
} from './useCycles';

// Detail hooks
export {
  useCycle,
  useActiveCycle,
  useCycleIssues,
  useCycleBurndown,
  useVelocity,
  usePrefetchCycle,
  useCycleCache,
  type UseCycleOptions,
  type UseCycleIssuesOptions,
  type UseCycleBurndownOptions,
  type UseVelocityOptions,
  type UseActiveCycleOptions,
} from './useCycle';

// Mutation hooks
export {
  useCreateCycle,
  useUpdateCycle,
  useDeleteCycle,
  useActivateCycle,
  useCompleteCycle,
  type UseCreateCycleOptions,
  type UseUpdateCycleOptions,
  type UseDeleteCycleOptions,
} from './useCreateCycle';

// Issue management hooks
export {
  useRolloverCycle,
  useAddIssueToCycle,
  useBulkAddIssuesToCycle,
  useRemoveIssueFromCycle,
  type UseRolloverCycleOptions,
  type UseAddIssueToCycleOptions,
  type UseRemoveIssueFromCycleOptions,
} from './useRolloverCycle';

// Release notes hooks
export { useReleaseNotes, type UseReleaseNotesOptions } from './useReleaseNotes';
