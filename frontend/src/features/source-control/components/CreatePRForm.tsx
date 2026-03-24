'use client';

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useGitWebStore } from '@/stores/RootStore';
import { useBranches } from '../hooks/useBranches';
import { useCreatePR } from '../hooks/useCreatePR';

/**
 * CreatePRForm - Inline form for creating pull requests from the SCM panel.
 *
 * observer() component for reading gitWebStore branch state.
 */
interface CreatePRFormProps {
  onClose: () => void;
}

export const CreatePRForm = observer(function CreatePRForm({ onClose }: CreatePRFormProps) {
  const gitWebStore = useGitWebStore();
  const { branches } = useBranches(gitWebStore.currentRepo);
  const { createPR, isCreating } = useCreatePR(gitWebStore.currentRepo);

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [baseBranch, setBaseBranch] = useState(gitWebStore.defaultBranch);
  const [draft, setDraft] = useState(false);

  const canSubmit = title.trim().length > 0 && !isCreating;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    createPR(
      {
        title: title.trim(),
        body,
        head: gitWebStore.currentBranch,
        base: baseBranch,
        draft,
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 px-2 py-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        New Pull Request
      </div>

      {/* Title */}
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Pull request title"
        className="h-7 text-xs"
        autoFocus
      />

      {/* Description */}
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Add a description..."
        className="min-h-[60px] text-xs resize-none"
        rows={3}
      />

      {/* Base branch selector */}
      <div className="flex items-center gap-2">
        <Label className="text-xs text-muted-foreground shrink-0">Base:</Label>
        <Select value={baseBranch} onValueChange={setBaseBranch}>
          <SelectTrigger className="h-7 text-xs flex-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {branches.map((b) => (
              <SelectItem key={b.name} value={b.name} className="text-xs">
                {b.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Head branch (read-only) */}
      <div className="flex items-center gap-2">
        <Label className="text-xs text-muted-foreground shrink-0">Head:</Label>
        <span className="text-xs font-mono truncate">{gitWebStore.currentBranch}</span>
      </div>

      {/* Draft checkbox */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="pr-draft"
          checked={draft}
          onCheckedChange={(checked) => setDraft(checked === true)}
        />
        <Label htmlFor="pr-draft" className="text-xs cursor-pointer">
          Create as draft
        </Label>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <Button type="submit" size="sm" className="h-7 text-xs flex-1" disabled={!canSubmit}>
          {isCreating ? 'Creating...' : 'Create Pull Request'}
        </Button>
        <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
});
