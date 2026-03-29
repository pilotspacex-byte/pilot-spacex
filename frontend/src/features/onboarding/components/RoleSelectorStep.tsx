'use client';

/**
 * RoleSelectorStep - Role selection grid for onboarding sub-flow.
 *
 * Renders a 3-column grid of RoleCards, handles multi-select (max 3),
 * displays selection summary, and routes to custom role input.
 *
 * Migrated from RoleSkillStore to props-based state management.
 * Source: FR-001, FR-002, FR-018, US1
 */
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RoleCard } from '@/components/role-skill/RoleCard';
import type { SDLCRoleType } from '../constants/skill-wizard-constants';
import type { SkillTemplate } from '@/services/api/skill-templates';

export interface RoleSelectorStepProps {
  /** User's profile default role (for badge display). */
  defaultRole?: SDLCRoleType | null;
  /** Workspace owner's suggested role (for badge display). */
  suggestedRole?: SDLCRoleType | null;
  /** Role types that already have a saved skill (shown as disabled). */
  existingSkillRoleTypes?: string[];
  /** Currently selected roles. */
  selectedRoles: SDLCRoleType[];
  /** Called when a role is toggled. */
  onToggleRole: (roleType: SDLCRoleType) => void;
  /** Skill templates to display. */
  templates?: SkillTemplate[];
  /** Whether templates are loading. */
  isLoadingTemplates?: boolean;
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

export function RoleSelectorStep({
  defaultRole,
  suggestedRole,
  existingSkillRoleTypes = [],
  selectedRoles,
  onToggleRole,
  templates,
  isLoadingTemplates = false,
  onContinue,
  onSkip,
  onBack,
  onCustomRole,
}: RoleSelectorStepProps) {
  const selectedCount = selectedRoles.length;
  const canContinue = selectedCount > 0;
  const remainingSlots = MAX_ROLES - selectedCount;
  const primaryRole = selectedRoles[0] ?? null;

  const handleToggle = (roleType: string) => {
    if (existingSkillRoleTypes.includes(roleType)) return;
    if (roleType === 'custom') {
      onCustomRole();
      return;
    }
    onToggleRole(roleType as SDLCRoleType);
  };

  if (isLoadingTemplates) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-3 text-sm text-muted-foreground">Loading skills...</p>
      </div>
    );
  }

  // Sort templates by sort_order, append custom option
  const sortedTemplates = [...(templates ?? [])].sort((a, b) => a.sort_order - b.sort_order);

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
        <h3 className="text-lg font-semibold">Set Up Your Skill</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Select a skill to personalize your AI assistant. Choose up to {MAX_ROLES} skills. The
          first selected becomes primary.
        </p>
      </div>

      {/* Role grid */}
      <div
        role="group"
        aria-label="Select your skills"
        className="grid grid-cols-3 gap-3 justify-items-center"
      >
        {sortedTemplates.map((template) => {
          const roleType = (template.role_type ?? template.name) as string;
          const isExisting = existingSkillRoleTypes.includes(roleType);
          const idx = selectedRoles.indexOf(roleType as SDLCRoleType);
          const isSelected = idx >= 0;
          const order = isSelected ? idx + 1 : null;
          const isDisabled = isExisting || (!isSelected && selectedCount >= MAX_ROLES);

          return (
            <RoleCard
              key={template.id}
              roleType={roleType}
              displayName={template.name}
              description={isExisting ? 'Already set up' : template.description}
              icon={template.icon}
              selected={isSelected}
              selectionOrder={order}
              isPrimary={isSelected && roleType === primaryRole}
              isDefaultRole={roleType === defaultRole}
              isSuggestedByOwner={roleType === suggestedRole}
              disabled={isDisabled}
              onToggle={() => handleToggle(roleType)}
            />
          );
        })}

        {/* Custom Skill card */}
        <RoleCard
          roleType="custom"
          displayName="Custom Skill"
          description="Define your own skill"
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
              {remainingSlots} more skill{remainingSlots > 1 ? 's' : ''} available
            </span>
          )}
        </div>
      )}

      {/* Live announcement for screen readers */}
      <div className="sr-only" aria-live="polite" role="status">
        {selectedCount} of {MAX_ROLES} skills selected.
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
}
