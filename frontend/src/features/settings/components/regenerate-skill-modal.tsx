/**
 * RegenerateSkillModal - Modal for regenerating a skill with diff preview.
 *
 * T039: Regeneration flow with experience textarea, AI generation, and diff view.
 * Source: FR-003, FR-015, US6
 */

'use client';

import * as React from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import type { RoleSkill, RegenerateSkillResponse } from '@/services/api/role-skills';

interface RegenerateSkillModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  skill: RoleSkill;
  onRegenerate: (experienceDescription: string) => Promise<RegenerateSkillResponse>;
  onAccept: (newContent: string, newName: string) => void;
  isRegenerating: boolean;
}

type ModalStep = 'input' | 'diff';

export function RegenerateSkillModal({
  open,
  onOpenChange,
  skill,
  onRegenerate,
  onAccept,
  isRegenerating,
}: RegenerateSkillModalProps) {
  const [step, setStep] = React.useState<ModalStep>('input');
  const [description, setDescription] = React.useState(skill.experienceDescription ?? '');
  const [regenerated, setRegenerated] = React.useState<RegenerateSkillResponse | null>(null);

  const handleGenerate = async () => {
    try {
      const result = await onRegenerate(description);
      setRegenerated(result);
      setStep('diff');
    } catch {
      // Error handled by the hook's onError toast
    }
  };

  const handleAccept = () => {
    if (regenerated) {
      onAccept(regenerated.skillContent, regenerated.suggestedRoleName);
    }
  };

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      setStep('input');
      setRegenerated(null);
    }
    onOpenChange(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-ai" />
            Regenerate {skill.roleName} Skill
          </DialogTitle>
          <DialogDescription>
            Update your experience description and generate a new skill.
          </DialogDescription>
        </DialogHeader>

        {step === 'input' && (
          <div className="space-y-4">
            <div>
              <label htmlFor="regen-description" className="text-sm font-medium">
                Update your experience description
              </label>
              <textarea
                id="regen-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={cn(
                  'mt-1.5 w-full min-h-[120px] rounded-lg border bg-background p-3',
                  'text-sm leading-relaxed resize-y',
                  'focus-visible:ring-[3px] focus-visible:ring-primary/30',
                  'focus-visible:outline-none focus-visible:border-primary'
                )}
                placeholder="Describe your experience, specializations, and how you like to work..."
                maxLength={5000}
              />
              <p className="mt-1 text-right text-xs text-muted-foreground">
                {description.length} / 5000 characters
              </p>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleGenerate}
                disabled={isRegenerating || description.trim().length < 10}
                className="bg-ai hover:bg-ai-hover text-white"
              >
                <Sparkles className="mr-1.5 h-4 w-4" />
                {isRegenerating ? 'Generating...' : 'Generate New Skill'}
              </Button>
            </div>
          </div>
        )}

        {step === 'diff' && regenerated && (
          <div className="space-y-4">
            <Separator />

            {/* Diff panels */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Current */}
              <div
                className="rounded-lg border bg-background-subtle p-3"
                aria-label="Current skill version"
              >
                <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                  Current
                </p>
                <div className="max-h-[300px] overflow-y-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
                  {regenerated.previousSkillContent}
                </div>
              </div>

              {/* New */}
              <div
                className="rounded-lg border border-ai-border bg-ai-muted p-3"
                aria-label="New skill version"
              >
                <p className="mb-2 text-xs font-semibold uppercase text-ai">
                  <Sparkles className="inline h-3 w-3 mr-1" />
                  New (AI Generated)
                </p>
                <div className="max-h-[300px] overflow-y-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
                  {regenerated.skillContent}
                </div>
              </div>
            </div>

            {/* Suggested name */}
            {regenerated.suggestedRoleName !== skill.roleName && (
              <p className="text-sm text-muted-foreground">
                Suggested role name:{' '}
                <span className="font-medium text-foreground">{regenerated.suggestedRoleName}</span>
              </p>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 justify-end">
              <Button variant="outline" onClick={() => handleClose(false)}>
                Keep Current
              </Button>
              <Button onClick={handleAccept}>Accept New Skill</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
