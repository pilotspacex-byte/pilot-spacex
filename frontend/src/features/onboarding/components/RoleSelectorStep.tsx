'use client';

/**
 * RoleSelectorStep - Role selection grid for onboarding sub-flow.
 *
 * Renders a 3-column grid of RoleCards, handles multi-select (max 3),
 * displays selection summary, and routes to custom role input.
 *
 * T020: Create RoleSelectorStep component
 * Source: FR-001, FR-002, FR-018, US1
 */
import { observer } from 'mobx-react-lite';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RoleCard } from '@/components/role-skill/RoleCard';
import { useRoleSkillStore } from '@/stores/RootStore';
import { useRoleTemplates } from '../hooks/useRoleSkillActions';
import type { SDLCRoleType } from '@/services/api/role-skills';
import type { RoleTemplate } from '@/services/api/role-skills';

export interface RoleSelectorStepProps {
  /** User's profile default role (for badge display). */
  defaultRole?: SDLCRoleType | null;
  /** Workspace owner's suggested role (for badge display). */
  suggestedRole?: SDLCRoleType | null;
  /** Role types that already have a saved skill (shown as disabled). */
  existingSkillRoleTypes?: SDLCRoleType[];
  /** Called when user clicks "Continue to Skill Setup". */
  onContinue: () => void;
  /** Called when user clicks "Skip". */
  onSkip: () => void;
  /** Called when user clicks "Back" (return to checklist). */
  onBack: () => void;
  /** Called when user selects "Custom Role" card. */
  onCustomRole: () => void;
}

const MAX_ROLES = 3;

/**
 * Build continue button text based on selection count.
 */
function getContinueLabel(count: number): string {
  if (count === 0) return 'Continue to Skill Setup';
  if (count === 1) return 'Continue to Skill Setup';
  return `Set Up ${count} Skills`;
}

export const RoleSelectorStep = observer(function RoleSelectorStep({
  defaultRole,
  suggestedRole,
  existingSkillRoleTypes = [],
  onContinue,
  onSkip,
  onBack,
  onCustomRole,
}: RoleSelectorStepProps) {
  const roleSkillStore = useRoleSkillStore();
  const { data: templates, isLoading } = useRoleTemplates();

  const selectedRoles = roleSkillStore.selectedRoles;
  const selectedCount = roleSkillStore.selectedCount;
  const canContinue = roleSkillStore.canContinue;
  const remainingSlots = roleSkillStore.remainingSlots;
  const primaryRole = roleSkillStore.primaryRole;

  const handleToggle = (roleType: SDLCRoleType) => {
    if (existingSkillRoleTypes.includes(roleType)) return;
    if (roleType === 'custom') {
      onCustomRole();
      return;
    }
    roleSkillStore.toggleRole(roleType);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-3 text-sm text-muted-foreground">Loading roles...</p>
      </div>
    );
  }

  // Sort templates by sortOrder, append custom option
  const sortedTemplates = [...(templates ?? [])].sort((a, b) => a.sortOrder - b.sortOrder);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          aria-label="Back to checklist"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button onClick={onSkip} className="text-sm text-muted-foreground hover:text-foreground">
          Skip
        </button>
      </div>

      {/* Title */}
      <div>
        <h3 className="text-lg font-semibold">Set Up Your Role</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Select your SDLC role to personalize your AI assistant. Choose up to {MAX_ROLES} roles.
          The first selected becomes primary.
        </p>
      </div>

      {/* Role grid */}
      <div
        role="group"
        aria-label="Select your SDLC roles"
        className="grid grid-cols-3 gap-3 justify-items-center"
      >
        {sortedTemplates.map((template: RoleTemplate) => {
          const isExisting = existingSkillRoleTypes.includes(template.roleType);
          const idx = selectedRoles.indexOf(template.roleType);
          const isSelected = idx >= 0;
          const order = isSelected ? idx + 1 : null;
          const isDisabled = isExisting || (!isSelected && selectedCount >= MAX_ROLES);

          return (
            <RoleCard
              key={template.roleType}
              roleType={template.roleType}
              displayName={template.displayName}
              description={isExisting ? 'Already set up' : template.description}
              icon={template.icon}
              selected={isSelected}
              selectionOrder={order}
              isPrimary={isSelected && template.roleType === primaryRole}
              isDefaultRole={template.roleType === defaultRole}
              isSuggestedByOwner={template.roleType === suggestedRole}
              disabled={isDisabled}
              onToggle={() => handleToggle(template.roleType)}
            />
          );
        })}

        {/* Custom Role card */}
        <RoleCard
          roleType="custom"
          displayName="Custom Role"
          description="Define your own role"
          icon="Pencil"
          selected={selectedRoles.includes('custom')}
          selectionOrder={
            selectedRoles.includes('custom') ? selectedRoles.indexOf('custom') + 1 : null
          }
          isPrimary={primaryRole === 'custom'}
          disabled={!selectedRoles.includes('custom') && selectedCount >= MAX_ROLES}
          onToggle={() => handleToggle('custom')}
        />
      </div>

      {/* Selection summary bar */}
      {selectedCount > 0 && (
        <div className="rounded-lg border bg-[#F7F5F2] p-3 text-sm" aria-live="polite">
          <span className="font-medium">
            Selected:{' '}
            {selectedRoles.map((r, i) => (
              <span key={r}>
                {i > 0 && ' \u00b7 '}
                {r.replace(/_/g, ' ')}
                {i === 0 && ' (primary)'}
              </span>
            ))}
          </span>
          {remainingSlots > 0 && (
            <span className="ml-2 text-muted-foreground">
              {remainingSlots} more role{remainingSlots > 1 ? 's' : ''} available
            </span>
          )}
        </div>
      )}

      {/* Live announcement for screen readers */}
      <div className="sr-only" aria-live="polite" role="status">
        {selectedCount} of {MAX_ROLES} roles selected.
        {primaryRole && ` ${primaryRole.replace(/_/g, ' ')} is primary.`}
      </div>

      {/* Continue button */}
      <div className="flex justify-end">
        <Button onClick={onContinue} disabled={!canContinue}>
          {getContinueLabel(selectedCount)}
          <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
});
