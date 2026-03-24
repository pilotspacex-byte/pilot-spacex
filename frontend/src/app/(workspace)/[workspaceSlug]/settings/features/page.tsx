/**
 * Features settings page — admin toggles for workspace sidebar modules.
 *
 * T008: 8 toggleable features in two groups: Main + AI.
 * Follows AISettingsPage error handling pattern (loading skeleton + error Alert).
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import {
  FileText,
  LayoutGrid,
  FolderKanban,
  Users,
  Network,
  UserCog,
  DollarSign,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useWorkspaceStore } from '@/stores/RootStore';
import { toast } from 'sonner';
import type { WorkspaceFeatureToggles } from '@/types';
import { DEFAULT_FEATURE_TOGGLES } from '@/types';

interface FeatureToggleItem {
  key: keyof WorkspaceFeatureToggles;
  label: string;
  description: string;
  icon: React.ElementType;
}

const mainFeatures: FeatureToggleItem[] = [
  {
    key: 'notes',
    label: 'Notes',
    description: 'Note-first workspace for writing, brainstorming, and AI ghost text',
    icon: FileText,
  },
  {
    key: 'issues',
    label: 'Issues',
    description: 'Issue tracker with AI-powered extraction and context generation',
    icon: LayoutGrid,
  },
  {
    key: 'projects',
    label: 'Projects',
    description: 'Project management with cycles, boards, and dependency graphs',
    icon: FolderKanban,
  },
  {
    key: 'members',
    label: 'Members',
    description: 'Member directory with roles, capacity planning, and contribution stats',
    icon: Users,
  },
  {
    key: 'knowledge',
    label: 'Knowledge',
    description: 'Knowledge graph for workspace-level code and dependency visualization',
    icon: Network,
  },
];

const aiFeatures: FeatureToggleItem[] = [
  {
    key: 'skills',
    label: 'Skills',
    description: 'AI skill library with custom templates and role-based skill assignment',
    icon: UserCog,
  },
  {
    key: 'costs',
    label: 'Costs',
    description: 'AI cost tracking and budget management per workspace',
    icon: DollarSign,
  },
  {
    key: 'approvals',
    label: 'Approvals',
    description: 'Human-in-the-loop approval workflow for destructive AI actions',
    icon: CheckCircle2,
  },
];

function LoadingSkeleton() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="space-y-2">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-80" />
      </div>
      <Skeleton className="h-[280px] w-full rounded-lg" />
      <Skeleton className="h-[200px] w-full rounded-lg" />
    </div>
  );
}

function FeatureToggle({
  item,
  checked,
  disabled,
  onCheckedChange,
}: {
  item: FeatureToggleItem;
  checked: boolean;
  disabled: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  const id = React.useId();
  const Icon = item.icon;

  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex items-start gap-3 flex-1">
        <div className="mt-1">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 space-y-1">
          <Label htmlFor={id} className="text-sm font-medium cursor-pointer">
            {item.label}
          </Label>
          <p className="text-sm text-muted-foreground">{item.description}</p>
        </div>
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        aria-label={`Toggle ${item.label}`}
      />
    </div>
  );
}

function FeatureGroup({
  title,
  description,
  features,
  toggles,
  disabled,
  onToggle,
}: {
  title: string;
  description: string;
  features: FeatureToggleItem[];
  toggles: WorkspaceFeatureToggles;
  disabled: boolean;
  onToggle: (key: keyof WorkspaceFeatureToggles, value: boolean) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1">
        {features.map((item, index) => (
          <React.Fragment key={item.key}>
            {index > 0 && <Separator />}
            <FeatureToggle
              item={item}
              checked={toggles[item.key]}
              disabled={disabled}
              onCheckedChange={(checked) => onToggle(item.key, checked)}
            />
          </React.Fragment>
        ))}
      </CardContent>
    </Card>
  );
}

const FeaturesSettingsPage = observer(function FeaturesSettingsPage() {
  const workspaceStore = useWorkspaceStore();
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;

  // Redirect non-admins to settings home
  React.useEffect(() => {
    if (workspaceStore.currentUserRole && !workspaceStore.isAdmin) {
      router.replace(`/${workspaceSlug}/settings`);
    }
  }, [workspaceStore.currentUserRole, workspaceStore.isAdmin, workspaceSlug, router]);

  const toggles = workspaceStore.featureToggles;
  const isDisabled = workspaceStore.isSaving || !toggles;

  const handleToggle = async (key: keyof WorkspaceFeatureToggles, value: boolean) => {
    const success = await workspaceStore.saveFeatureToggles({ [key]: value });
    if (success) {
      toast.success(`${key.charAt(0).toUpperCase() + key.slice(1)} ${value ? 'enabled' : 'disabled'}`);
    } else {
      toast.error('Failed to update feature toggle', {
        description: workspaceStore.error ?? undefined,
      });
    }
  };

  if (!workspaceStore.isAdmin) {
    return null;
  }

  // Loading state — toggles not yet fetched
  if (!toggles && !workspaceStore.error) {
    return <LoadingSkeleton />;
  }

  // Error state — failed to load toggles
  if (workspaceStore.error && !toggles) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load feature toggles</AlertTitle>
          <AlertDescription>{workspaceStore.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h2 className="text-lg font-semibold">Features</h2>
        <p className="text-sm text-muted-foreground">
          Control which modules are visible in the sidebar for all workspace members.
        </p>
      </div>

      <FeatureGroup
        title="Main Modules"
        description="Core workspace modules visible to all members"
        features={mainFeatures}
        toggles={toggles ?? DEFAULT_FEATURE_TOGGLES}
        disabled={isDisabled}
        onToggle={handleToggle}
      />

      <FeatureGroup
        title="AI Modules"
        description="AI-powered workspace features"
        features={aiFeatures}
        toggles={toggles ?? DEFAULT_FEATURE_TOGGLES}
        disabled={isDisabled}
        onToggle={handleToggle}
      />
    </div>
  );
});

export default FeaturesSettingsPage;
