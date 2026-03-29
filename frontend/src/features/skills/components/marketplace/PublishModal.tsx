/**
 * PublishModal - Dialog for publishing a workspace skill template to the marketplace.
 *
 * Collects listing metadata (name, description, author, category, version, tags, icon)
 * and calls the usePublishListing mutation.
 * Source: Phase 055, P55-04
 */

'use client';

import * as React from 'react';

import {
  Code,
  Container,
  FileSearch,
  GanttChart,
  GitBranch,
  Layers,
  Loader2,
  Pencil,
  Target,
  TestTube,
  Wand2,
  type LucideIcon,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/stores';

import { usePublishListing } from '../../hooks/use-marketplace';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES = [
  'Development',
  'Writing',
  'Analysis',
  'Documentation',
  'Security',
  'Design',
] as const;

const ICON_MAP: Record<string, LucideIcon> = {
  Wand2, Code, FileSearch, Target, Layers, GitBranch, TestTube, Container, GanttChart, Pencil,
};
const ICON_OPTIONS = Object.keys(ICON_MAP) as (keyof typeof ICON_MAP)[];

const SEMVER_REGEX = /^\d+\.\d+\.\d+$/;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PublishModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  skillTemplateId: string;
  skillTemplateName: string;
  workspaceId: string;
}

interface FormState {
  name: string;
  description: string;
  longDescription: string;
  author: string;
  category: string;
  version: string;
  icon: string;
  tags: string;
}

interface FormErrors {
  name?: string;
  description?: string;
  author?: string;
  category?: string;
  version?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PublishModal({
  open,
  onOpenChange,
  skillTemplateId,
  skillTemplateName,
  workspaceId,
}: PublishModalProps) {
  const { authStore } = useStore();
  const publishListing = usePublishListing(workspaceId);

  const [form, setForm] = React.useState<FormState>({
    name: skillTemplateName,
    description: '',
    longDescription: '',
    author: authStore.userDisplayName || '',
    category: CATEGORIES[0],
    version: '1.0.0',
    icon: 'Wand2',
    tags: '',
  });

  const [errors, setErrors] = React.useState<FormErrors>({});
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  // Reset form when modal opens with new template
  React.useEffect(() => {
    if (open) {
      setForm({
        name: skillTemplateName,
        description: '',
        longDescription: '',
        author: authStore.userDisplayName || '',
        category: CATEGORIES[0],
        version: '1.0.0',
        icon: 'Wand2',
        tags: '',
      });
      setErrors({});
      setSubmitError(null);
    }
  }, [open, skillTemplateName, authStore.userDisplayName]);

  // ---------------------------------------------------------------------------
  // Validation
  // ---------------------------------------------------------------------------

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!form.name || form.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters';
    }
    if (!form.description.trim()) {
      newErrors.description = 'Description is required';
    }
    if (!form.author.trim()) {
      newErrors.author = 'Author is required';
    }
    if (!form.category) {
      newErrors.category = 'Category is required';
    }
    if (!SEMVER_REGEX.test(form.version)) {
      newErrors.version = 'Version must be in X.Y.Z format (e.g. 1.0.0)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validate()) return;

    const tagsArray = form.tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    publishListing.mutate(
      {
        skillTemplateId,
        data: {
          name: form.name,
          description: form.description,
          longDescription: form.longDescription || null,
          author: form.author,
          category: form.category,
          version: form.version,
          icon: form.icon || undefined,
          tags: tagsArray,
        },
      },
      {
        onSuccess: () => {
          toast.success('Published to Marketplace!');
          onOpenChange(false);
        },
        onError: (err) => {
          const message =
            err instanceof Error ? err.message : 'Failed to publish listing';
          setSubmitError(message);
        },
      },
    );
  };

  // ---------------------------------------------------------------------------
  // Field helper
  // ---------------------------------------------------------------------------

  const updateField = <K extends keyof FormState>(
    key: K,
    value: FormState[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Publish to Marketplace</DialogTitle>
          <DialogDescription>
            Share &quot;{skillTemplateName}&quot; with the marketplace community.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="publish-name">Name *</Label>
            <Input
              id="publish-name"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="Skill name"
              aria-invalid={!!errors.name}
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label htmlFor="publish-description">Description *</Label>
            <Textarea
              id="publish-description"
              value={form.description}
              onChange={(e) => updateField('description', e.target.value)}
              placeholder="Brief description of what this skill does"
              rows={2}
              aria-invalid={!!errors.description}
            />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description}</p>
            )}
          </div>

          {/* Long Description */}
          <div className="space-y-1.5">
            <Label htmlFor="publish-long-desc">
              Long Description{' '}
              <span className="text-muted-foreground font-normal">
                (optional)
              </span>
            </Label>
            <Textarea
              id="publish-long-desc"
              value={form.longDescription}
              onChange={(e) => updateField('longDescription', e.target.value)}
              placeholder="Detailed description, usage examples, etc."
              rows={4}
            />
          </div>

          {/* Author */}
          <div className="space-y-1.5">
            <Label htmlFor="publish-author">Author *</Label>
            <Input
              id="publish-author"
              value={form.author}
              onChange={(e) => updateField('author', e.target.value)}
              placeholder="Your name"
              aria-invalid={!!errors.author}
            />
            {errors.author && (
              <p className="text-xs text-destructive">{errors.author}</p>
            )}
          </div>

          {/* Category + Version row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="publish-category">Category *</Label>
              <Select
                value={form.category}
                onValueChange={(v) => updateField('category', v)}
              >
                <SelectTrigger id="publish-category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.category && (
                <p className="text-xs text-destructive">{errors.category}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="publish-version">Version *</Label>
              <Input
                id="publish-version"
                value={form.version}
                onChange={(e) => updateField('version', e.target.value)}
                placeholder="1.0.0"
                aria-invalid={!!errors.version}
              />
              {errors.version && (
                <p className="text-xs text-destructive">{errors.version}</p>
              )}
            </div>
          </div>

          {/* Icon picker */}
          <div className="space-y-1.5">
            <Label>Icon</Label>
            <div className="flex flex-wrap gap-1.5">
              {ICON_OPTIONS.map((iconName) => {
                const IconComp = ICON_MAP[iconName];
                return (
                  <button
                    key={iconName}
                    type="button"
                    onClick={() => updateField('icon', iconName)}
                    aria-pressed={form.icon === iconName}
                    className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                      form.icon === iconName
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-background text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    {IconComp && <IconComp size={14} />}
                    {iconName}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tags */}
          <div className="space-y-1.5">
            <Label htmlFor="publish-tags">
              Tags{' '}
              <span className="text-muted-foreground font-normal">
                (comma-separated)
              </span>
            </Label>
            <Input
              id="publish-tags"
              value={form.tags}
              onChange={(e) => updateField('tags', e.target.value)}
              placeholder="e.g. python, code-review, testing"
            />
          </div>

          {/* Submit error */}
          {submitError && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
              <p className="text-sm text-destructive">{submitError}</p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={publishListing.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={publishListing.isPending}>
              {publishListing.isPending && (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              )}
              Publish to Marketplace
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
