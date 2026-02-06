/**
 * SkillsSettingsPage - Workspace AI Skills configuration.
 *
 * T038: Main settings page for managing role-based skills (CRUD operations).
 * Source: FR-009, FR-010, FR-015, FR-018, US6
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Lock, Plus, Wand2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useStore } from '@/stores';
import {
  useRoleSkills,
  useRoleTemplates,
  useUpdateRoleSkill,
  useRegenerateSkill,
  useDeleteRoleSkill,
} from '@/features/onboarding/hooks';
import { SkillCard } from '../components/skill-card';
import { RegenerateSkillModal } from '../components/regenerate-skill-modal';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';
import type { RoleSkill } from '@/services/api/role-skills';

const MAX_ROLES = 3;

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-[200px] w-full" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}

function EmptyState({ onSetup }: { onSetup: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <Wand2 className="h-20 w-20 text-muted-foreground opacity-40" />
      <h2 className="text-lg font-medium text-foreground">No roles configured</h2>
      <p className="text-sm text-muted-foreground max-w-[280px] text-center">
        Set up your SDLC role to personalize how the AI assistant helps you in this workspace.
      </p>
      <Button onClick={onSetup}>
        <Plus className="mr-1.5 h-4 w-4" />
        Set Up Your Role
      </Button>
    </div>
  );
}

function GuestView() {
  return (
    <div className="py-8">
      <Alert role="alert">
        <Lock className="h-4 w-4" />
        <AlertDescription>
          Role skill configuration requires Member or higher access. Contact a workspace admin for
          permission.
        </AlertDescription>
      </Alert>
    </div>
  );
}

export const SkillsSettingsPage = observer(function SkillsSettingsPage() {
  const { workspaceStore, roleSkillStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  // Server state
  const { data: skills, isLoading, isError, error } = useRoleSkills(workspaceId);
  const { data: templates } = useRoleTemplates();
  const updateSkill = useUpdateRoleSkill({ workspaceId });
  const regenerateSkill = useRegenerateSkill({ workspaceId });
  const deleteSkill = useDeleteRoleSkill({ workspaceId });

  // UI state
  const [regenerateTarget, setRegenerateTarget] = React.useState<RoleSkill | null>(null);
  const [removeTarget, setRemoveTarget] = React.useState<RoleSkill | null>(null);
  const [resetTarget, setResetTarget] = React.useState<RoleSkill | null>(null);

  const skillCount = skills?.length ?? 0;
  const slotsLeft = MAX_ROLES - skillCount;
  const isMaxReached = skillCount >= MAX_ROLES;

  // Check if user is guest
  const isGuest = workspaceStore.currentUserRole === 'guest';

  const handleEdit = (skillId: string, content: string) => {
    updateSkill.mutate(
      { skillId, payload: { skillContent: content } },
      { onSuccess: () => roleSkillStore.clearEditingSkillId() }
    );
  };

  const handleRegenerate = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setRegenerateTarget(skill);
  };

  const handleRegenerateSubmit = async (experienceDescription: string) => {
    if (!regenerateTarget) throw new Error('No target skill');
    return regenerateSkill.mutateAsync({
      skillId: regenerateTarget.id,
      payload: { experienceDescription: experienceDescription },
    });
  };

  const handleRegenerateAccept = (newContent: string, newName: string) => {
    if (!regenerateTarget) return;
    updateSkill.mutate(
      {
        skillId: regenerateTarget.id,
        payload: { skillContent: newContent, roleName: newName },
      },
      { onSuccess: () => setRegenerateTarget(null) }
    );
  };

  const handleReset = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setResetTarget(skill);
  };

  const handleResetConfirm = () => {
    if (!resetTarget || !templates) return;
    const template = templates.find((t) => t.roleType === resetTarget.roleType);
    if (template) {
      updateSkill.mutate(
        {
          skillId: resetTarget.id,
          payload: {
            skillContent: template.defaultSkillContent,
            roleName: template.displayName,
          },
        },
        { onSuccess: () => setResetTarget(null) }
      );
    }
  };

  const handleRemove = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setRemoveTarget(skill);
  };

  const handleRemoveConfirm = () => {
    if (!removeTarget) return;
    deleteSkill.mutate(removeTarget.id, {
      onSuccess: () => setRemoveTarget(null),
    });
  };

  const handleSetupRole = () => {
    roleSkillStore.setGenerationStep('select');
  };

  if (isGuest) {
    return (
      <div className="max-w-3xl px-8 py-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">AI Skills</h1>
        </div>
        <GuestView />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl px-8 py-6">
        <LoadingSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-3xl px-8 py-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load skills: {error?.message ?? 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl px-8 py-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">AI Skills</h1>
            <p className="text-sm text-muted-foreground">
              Configure how the AI assistant adapts to your role.
            </p>
          </div>
          <div className="text-right">
            <Button
              onClick={handleSetupRole}
              disabled={isMaxReached}
              aria-describedby={isMaxReached ? 'max-roles-hint' : undefined}
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Add Role
            </Button>
            {!isMaxReached && slotsLeft > 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                {slotsLeft} slot{slotsLeft > 1 ? 's' : ''} left
              </p>
            )}
          </div>
        </div>

        {/* Max roles warning */}
        {isMaxReached && (
          <Alert id="max-roles-hint">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Maximum {MAX_ROLES} roles per workspace reached. Remove an existing role to add a new
              one.
            </AlertDescription>
          </Alert>
        )}

        {/* Skills list or empty state */}
        {skills && skills.length > 0 ? (
          <div className="space-y-4">
            {skills
              .slice()
              .sort((a, b) => {
                if (a.isPrimary && !b.isPrimary) return -1;
                if (!a.isPrimary && b.isPrimary) return 1;
                return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
              })
              .map((skill) => (
                <SkillCard
                  key={skill.id}
                  skill={skill}
                  onEdit={handleEdit}
                  onRegenerate={handleRegenerate}
                  onReset={handleReset}
                  onRemove={handleRemove}
                  isSaving={updateSkill.isPending}
                />
              ))}
          </div>
        ) : (
          <EmptyState onSetup={handleSetupRole} />
        )}
      </div>

      {/* Regenerate Modal */}
      {regenerateTarget && (
        <RegenerateSkillModal
          open={!!regenerateTarget}
          onOpenChange={(open) => !open && setRegenerateTarget(null)}
          skill={regenerateTarget}
          onRegenerate={handleRegenerateSubmit}
          onAccept={handleRegenerateAccept}
          isRegenerating={regenerateSkill.isPending}
        />
      )}

      {/* Remove Confirmation */}
      {removeTarget && (
        <ConfirmActionDialog
          open={!!removeTarget}
          onCancel={() => setRemoveTarget(null)}
          onConfirm={handleRemoveConfirm}
          title={`Remove ${removeTarget.roleName} Role?`}
          description={`This will deactivate the ${removeTarget.roleName} skill for this workspace. The AI assistant will no longer use ${removeTarget.roleName}-specific behavior in your conversations. Your skill content will be permanently deleted.`}
          confirmLabel="Remove Role"
          variant="destructive"
        />
      )}

      {/* Reset Confirmation */}
      {resetTarget && (
        <ConfirmActionDialog
          open={!!resetTarget}
          onCancel={() => setResetTarget(null)}
          onConfirm={handleResetConfirm}
          title="Reset to Default Template?"
          description={`This will replace your custom ${resetTarget.roleName} skill with the default ${resetTarget.roleType.replace(/_/g, ' ')} template. All customizations will be lost.`}
          confirmLabel="Reset Skill"
          variant="destructive"
        />
      )}
    </div>
  );
});
