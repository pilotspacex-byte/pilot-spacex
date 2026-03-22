/**
 * AIFeatureToggles - Feature toggle switches for AI capabilities.
 *
 * Shows inline guidance when prerequisites are not met.
 * Stops event propagation on disabled switches to prevent dialog dismissal.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, FileText, MessageSquare, GitPullRequest, Lightbulb, Info } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores';

interface FeatureToggleProps {
  icon: React.ElementType;
  label: string;
  description: string;
  checked: boolean;
  disabled: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function FeatureToggle({
  icon: Icon,
  label,
  description,
  checked,
  disabled,
  onCheckedChange,
}: FeatureToggleProps) {
  const id = React.useId();

  return (
    <div
      className="flex items-center justify-between py-3"
      onClick={(e) => {
        // Prevent disabled toggle clicks from bubbling up to dialog overlay
        if (disabled) {
          e.stopPropagation();
        }
      }}
    >
      <div className="flex items-start gap-3 flex-1">
        <div className="mt-0.5">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 space-y-0.5">
          <Label htmlFor={id} className="text-sm font-medium cursor-pointer">
            {label}
          </Label>
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
      </div>
      <div
        onClick={(e) => {
          // Extra safety: stop propagation on the switch wrapper
          if (disabled) {
            e.stopPropagation();
            e.preventDefault();
          }
        }}
      >
        <Switch
          id={id}
          checked={checked}
          onCheckedChange={onCheckedChange}
          disabled={disabled}
          aria-label={`Toggle ${label}`}
        />
      </div>
    </div>
  );
}

export const AIFeatureToggles = observer(function AIFeatureToggles() {
  const { ai } = useStore();
  const { settings } = ai;

  const handleToggle = async (feature: string, enabled: boolean) => {
    try {
      await settings.saveSettings({ features: { [feature]: enabled } });
    } catch (error) {
      console.error('Failed to toggle feature:', error);
    }
  };

  const hasEmbedding = settings.embeddingConfigured;
  const hasLlm = settings.llmConfigured;
  const allKeysConfigured = hasLlm && hasEmbedding;
  const isDisabled = settings.isSaving || !allKeysConfigured;

  // Build guidance message
  const getMissingMessage = (): string | null => {
    if (allKeysConfigured) return null;
    const missing: string[] = [];
    if (!hasEmbedding) missing.push('Embedding');
    if (!hasLlm) missing.push('LLM');
    return `Configure ${missing.join(' and ')} provider${missing.length > 1 ? 's' : ''} above to enable features.`;
  };

  const missingMessage = getMissingMessage();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Features</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Enable or disable AI capabilities for your workspace.
          </p>
        </div>
      </div>

      {missingMessage && (
        <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2.5">
          <Info className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <p className="text-xs text-muted-foreground">{missingMessage}</p>
        </div>
      )}

      <div
        className={cn(
          'rounded-lg border border-border bg-background px-4 transition-opacity',
          isDisabled && 'opacity-60 pointer-events-auto'
        )}
      >
        <FeatureToggle
          icon={Sparkles}
          label="Ghost Text Suggestions"
          description="Real-time AI text completions while writing notes"
          checked={settings.ghostTextEnabled}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('ghost_text_enabled', checked)}
        />
        <Separator />
        <FeatureToggle
          icon={MessageSquare}
          label="Margin Annotations"
          description="AI suggestions displayed in note margins"
          checked={settings.marginAnnotationsEnabled}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('margin_annotations_enabled', checked)}
        />
        <Separator />
        <FeatureToggle
          icon={FileText}
          label="AI Context Generation"
          description="Automatically generate implementation context for issues"
          checked={settings.aiContextEnabled}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('ai_context_enabled', checked)}
        />
        <Separator />
        <FeatureToggle
          icon={Lightbulb}
          label="Issue Extraction"
          description="Extract actionable issues from notes using AI"
          checked={settings.settings?.features?.issueExtractionEnabled ?? false}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('issue_extraction_enabled', checked)}
        />
        <Separator />
        <FeatureToggle
          icon={GitPullRequest}
          label="PR Review"
          description="AI-powered pull request reviews"
          checked={settings.settings?.features?.prReviewEnabled ?? false}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('pr_review_enabled', checked)}
        />
      </div>
    </div>
  );
});
