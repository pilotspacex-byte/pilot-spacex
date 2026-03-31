/**
 * AIChatProjectSelector - Compact project picker in ChatHeader.
 *
 * Visible only when the current user has 2+ active (non-archived) project
 * memberships. Selecting a project:
 *   1. Updates `pilotSpace.projectContext` (MobX) → flows into next message's
 *      `context.project_id` via `conversationContext` computed property.
 *   2. Persists `last_active_project_id` via PATCH …/me/last-active-project.
 *
 * Admins/owners see all projects (returned by listMyProjects); members/guests
 * see only their assigned projects.
 *
 * @module features/ai/ChatView/AIChatProjectSelector
 */
'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MyProjectCard } from '@/services/api/project-members';
import { projectMembersApi, useMyProjects } from '@/services/api/project-members';
import { useStore } from '@/stores';
import { observer } from 'mobx-react-lite';
import { useEffect } from 'react';

export const AIChatProjectSelector = observer(function AIChatProjectSelector() {
  const { ai } = useStore();
  const { pilotSpace } = ai;
  const workspaceId = pilotSpace.workspaceId ?? '';

  const { data } = useMyProjects(workspaceId);
  const activeProjects: MyProjectCard[] =
    data?.items.filter((p: MyProjectCard) => !p.isArchived) ?? [];

  // T046: Auto-initialize project context on first load (before any UI render).
  // When the store has no active project yet and projects have loaded, seed the
  // first project so `conversationContext.project_id` is populated immediately.
  const firstId = activeProjects[0]?.projectId;
  const firstName = activeProjects[0]?.name;
  const firstIdentifier = activeProjects[0]?.identifier;
  useEffect(() => {
    if (firstId && !pilotSpace.projectContext) {
      pilotSpace.setProjectContext({ projectId: firstId, name: firstName, slug: firstIdentifier });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstId, firstName, firstIdentifier]);

  // Only render selector UI when user belongs to 2+ active projects
  if (!workspaceId || activeProjects.length < 2) return null;

  const selectedProjectId = pilotSpace.projectContext?.projectId ?? '';

  const handleChange = (projectId: string) => {
    const project = activeProjects.find((p: MyProjectCard) => p.projectId === projectId);
    if (!project) return;

    // Update MobX store so next sendMessage includes project_id in context
    pilotSpace.setProjectContext({
      projectId: project.projectId,
      name: project.name,
      slug: project.identifier,
    });

    // Persist as last_active_project_id (non-blocking; backend also updates
    // via fire-and-forget on AI session start per T044).
    projectMembersApi.updateLastActiveProject(workspaceId, projectId).catch(() => {
      // Non-critical — backend will apply the update on next message send
    });
  };

  return (
    <Select value={selectedProjectId} onValueChange={handleChange}>
      <SelectTrigger
        className="h-6 w-[130px] text-xs border-border/50 bg-transparent"
        data-testid="ai-project-selector"
      >
        <SelectValue placeholder="Project" />
      </SelectTrigger>
      <SelectContent>
        {activeProjects.map((p: MyProjectCard) => (
          <SelectItem key={p.projectId} value={p.projectId}>
            <span className="font-mono text-xs text-muted-foreground mr-1.5">{p.identifier}</span>
            <span className="truncate">{p.name}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
});

AIChatProjectSelector.displayName = 'AIChatProjectSelector';
