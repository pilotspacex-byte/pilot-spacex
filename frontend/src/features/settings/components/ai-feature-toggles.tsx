/**
 * AIFeatureToggles - Feature toggle switches for AI capabilities.
 *
 * T181: Toggle switches for ghost text, annotations, AI context, issue extraction, PR review.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, FileText, MessageSquare, GitPullRequest, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
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
    <div className="flex items-center justify-between py-3">
      <div className="flex items-start gap-3 flex-1">
        <div className="mt-1">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 space-y-1">
          <Label htmlFor={id} className="text-sm font-medium cursor-pointer">
            {label}
          </Label>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        aria-label={`Toggle ${label}`}
      />
    </div>
  );
}

export const AIFeatureToggles = observer(function AIFeatureToggles() {
  const { ai } = useStore();
  const { settings } = ai;

  const handleToggle = async (feature: string, enabled: boolean) => {
    try {
      await settings.saveSettings({ [feature]: enabled });
    } catch (error) {
      // Error handling already done in store
      console.error('Failed to toggle feature:', error);
    }
  };

  const allKeysConfigured = settings.anthropicKeySet && settings.openaiKeySet;
  const isDisabled = settings.isSaving || !allKeysConfigured;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>AI Features</CardTitle>
            <CardDescription>
              Enable or disable specific AI capabilities for your workspace
            </CardDescription>
          </div>
          {!allKeysConfigured && (
            <Badge variant="outline" className="text-muted-foreground">
              API keys required
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className={cn('space-y-1', isDisabled && 'opacity-60')}>
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
          description="AI suggestions and improvements displayed in note margins"
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
          checked={settings.settings?.issue_extraction_enabled ?? false}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('issue_extraction_enabled', checked)}
        />
        <Separator />
        <FeatureToggle
          icon={GitPullRequest}
          label="PR Review"
          description="AI-powered pull request reviews with architecture and security analysis"
          checked={settings.settings?.pr_review_enabled ?? false}
          disabled={isDisabled}
          onCheckedChange={(checked) => handleToggle('pr_review_enabled', checked)}
        />
      </CardContent>
    </Card>
  );
});
