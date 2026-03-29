/**
 * SkillSaveDialog — Save dialog with personal/workspace options.
 * Invalidates TanStack Query skills cache on successful save.
 *
 * @module features/ai/ChatView/SkillEditor/SkillSaveDialog
 */
'use client';

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, Shield, User, Users } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores/RootStore';
import { saveGeneratedSkill } from '@/services/api/skills';

type SaveType = 'personal' | 'workspace';

export const SkillSaveDialog = observer(function SkillSaveDialog() {
  const { aiStore, workspaceStore } = useStore();
  const skillStore = aiStore.pilotSpace.skillGeneratorStore;
  const workspaceId = aiStore.pilotSpace.workspaceId;
  const isAdmin = workspaceStore.isAdmin;
  const draft = skillStore.currentDraft;
  const queryClient = useQueryClient();

  const [saveType, setSaveType] = useState<SaveType>('personal');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!draft || !workspaceId) return;
    setIsSaving(true);
    try {
      await saveGeneratedSkill({
        workspaceId,
        sessionId: draft.sessionId,
        saveType,
        name: draft.name,
        description: draft.description,
        category: draft.category,
        icon: draft.icon,
        skillContent: draft.skillContent,
        examplePrompts: draft.examplePrompts,
        graphData: draft.graphData as Record<string, unknown> | null,
      });

      toast.success('Skill saved!', {
        description: `"${draft.name}" is now available${saveType === 'workspace' ? ' to all workspace members' : ''}.`,
      });

      // Invalidate all skill-related caches so SkillMenu updates immediately
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['user-skills'] }),
        queryClient.invalidateQueries({ queryKey: ['skill-templates'] }),
        queryClient.invalidateQueries({ queryKey: ['skills'] }),
      ]);

      // Store will also receive skill_saved SSE event which clears the draft
      skillStore.closeSaveDialog();
    } catch {
      toast.error('Failed to save skill', {
        description: 'Please try again or check your connection.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={skillStore.isSaveDialogOpen}
      onOpenChange={(open) => {
        if (!open) skillStore.closeSaveDialog();
      }}
    >
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Save Skill</DialogTitle>
          <DialogDescription>
            Choose where to save &ldquo;{draft?.name ?? 'skill'}&rdquo;.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-2">
          {/* Personal option */}
          <button
            type="button"
            onClick={() => setSaveType('personal')}
            className={cn(
              'flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
              saveType === 'personal'
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/40',
            )}
            data-testid="save-option-personal"
          >
            <div className="mt-0.5 h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
              <User className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium">Save as Personal</p>
              <p className="text-xs text-muted-foreground">Only you can use this skill</p>
            </div>
          </button>

          {/* Workspace option */}
          <button
            type="button"
            disabled={!isAdmin}
            onClick={() => {
              if (isAdmin) setSaveType('workspace');
            }}
            className={cn(
              'flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
              !isAdmin && 'opacity-50 cursor-not-allowed',
              isAdmin && saveType === 'workspace'
                ? 'border-primary bg-primary/5'
                : isAdmin
                  ? 'border-border hover:border-primary/40'
                  : 'border-border',
            )}
            data-testid="save-option-workspace"
          >
            <div className="mt-0.5 h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
              <Users className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium">Save to Workspace</p>
              <p className="text-xs text-muted-foreground">
                Available to all workspace members
              </p>
              {!isAdmin && (
                <span className="inline-flex items-center gap-1 mt-1 text-xs text-amber-600 dark:text-amber-400">
                  <Shield className="h-3 w-3" />
                  Requires admin approval
                </span>
              )}
            </div>
          </button>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => skillStore.closeSaveDialog()}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving || !draft}
            className="gap-1.5"
            data-testid="confirm-save-btn"
          >
            {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

SkillSaveDialog.displayName = 'SkillSaveDialog';
