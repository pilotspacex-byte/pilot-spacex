/**
 * Onboarding hooks - TanStack Query hooks for onboarding feature
 *
 * T019/T020: Create onboarding hooks
 * Source: FR-001, FR-002, FR-003, FR-005, FR-011, FR-013
 */

export {
  useOnboardingState,
  onboardingKeys,
  selectIsComplete,
  selectIsDismissed,
  selectCompletionPercentage,
  selectNextIncompleteStep,
} from './useOnboardingState';

export {
  useUpdateOnboardingStep,
  useDismissOnboarding,
  useValidateProviderKey,
  useCreateGuidedNote,
  useOnboardingActions,
} from './useOnboardingActions';

export {
  useRoleTemplates,
  useRoleSkills,
  useGenerateSkill,
  useCreateRoleSkill,
  useUpdateRoleSkill,
  useRegenerateSkill,
  useDeleteRoleSkill,
  roleSkillKeys,
} from './useRoleSkillActions';
