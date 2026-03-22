'use client';

import * as React from 'react';
import { lazy, Suspense } from 'react';
import { observer } from 'mobx-react-lite';
import {
  BarChart3,
  Building2,
  ClipboardList,
  CreditCard,
  KeyRound,
  Plug,
  ServerCog,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  Sparkles,
  User,
  Users,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useWorkspaceStore } from '@/stores/RootStore';
import { useSettingsModal } from './settings-modal-context';
import type { SettingsSection } from './settings-modal-context';

// Lazy-load all settings pages to avoid loading everything at once
const WorkspaceGeneralPage = lazy(() =>
  import('./pages/workspace-general-page').then((m) => ({ default: m.WorkspaceGeneralPage }))
);
const ProfileSettingsPage = lazy(() =>
  import('./pages/profile-settings-page').then((m) => ({ default: m.ProfileSettingsPage }))
);
const AISettingsPage = lazy(() =>
  import('./pages/ai-settings-page').then((m) => ({ default: m.AISettingsPage }))
);
const MCPServersSettingsPage = lazy(() =>
  import('./pages/mcp-servers-settings-page').then((m) => ({ default: m.MCPServersSettingsPage }))
);
const RolesSettingsPage = lazy(() =>
  import('./pages/roles-settings-page').then((m) => ({ default: m.RolesSettingsPage }))
);
const SecuritySettingsPage = lazy(() =>
  import('./pages/security-settings-page').then((m) => ({ default: m.SecuritySettingsPage }))
);
const AuditSettingsPage = lazy(() =>
  import('./pages/audit-settings-page').then((m) => ({ default: m.AuditSettingsPage }))
);
const EncryptionSettingsPage = lazy(() =>
  import('./pages/encryption-settings-page').then((m) => ({ default: m.EncryptionSettingsPage }))
);
const AIGovernanceSettingsPage = lazy(() =>
  import('./pages/ai-governance-settings-page').then((m) => ({
    default: m.AIGovernanceSettingsPage,
  }))
);
const UsageSettingsPage = lazy(() =>
  import('./pages/usage-settings-page').then((m) => ({ default: m.UsageSettingsPage }))
);
const SsoSettingsPage = lazy(() =>
  import('./pages/sso-settings-page').then((m) => ({ default: m.SsoSettingsPage }))
);
const SkillsSettingsPage = lazy(() =>
  import('./pages/skills-settings-page').then((m) => ({ default: m.SkillsSettingsPage }))
);
const IntegrationsSettingsPage = lazy(
  () => import('@/app/(workspace)/[workspaceSlug]/settings/integrations/page')
);
const FeaturesSettingsPage = lazy(
  () => import('@/app/(workspace)/[workspaceSlug]/settings/features/page')
);

// Billing placeholder (inline — trivial component)
function BillingPlaceholder() {
  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-foreground">Billing</h2>
        <p className="text-sm text-muted-foreground">Manage your workspace plan and usage.</p>
      </div>
      <div className="flex flex-col items-center justify-center rounded-xl bg-background-subtle p-12 text-center shadow-warm-sm">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-muted">
          <CreditCard className="h-6 w-6 text-primary" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-foreground">Free &amp; open source</h3>
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground leading-relaxed">
          Pilot Space is free and open source. Paid tiers with support SLAs will be available in a
          future release.
        </p>
      </div>
    </div>
  );
}

interface NavItem {
  id: SettingsSection;
  label: string;
  icon: React.ElementType;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const settingsNavSections: NavSection[] = [
  {
    label: 'Workspace',
    items: [
      { id: 'general', label: 'General', icon: Building2 },
      { id: 'features', label: 'Features', icon: Sliders },
      { id: 'ai-providers', label: 'AI Providers', icon: Sparkles },
      { id: 'mcp-servers', label: 'MCP Servers', icon: ServerCog },
      { id: 'integrations', label: 'Integrations', icon: Plug },
      { id: 'sso', label: 'SSO', icon: Shield },
      { id: 'encryption', label: 'Encryption', icon: KeyRound },
      { id: 'ai-governance', label: 'AI Governance', icon: ShieldCheck },
      { id: 'audit', label: 'Audit', icon: ClipboardList },
      { id: 'roles', label: 'Custom Roles', icon: Users },
      { id: 'usage', label: 'Usage', icon: BarChart3 },
      { id: 'billing', label: 'Billing', icon: CreditCard },
    ],
  },
  {
    label: 'Account',
    items: [{ id: 'profile', label: 'Profile', icon: User }],
  },
];

const SECTION_COMPONENTS: Record<
  SettingsSection,
  React.LazyExoticComponent<React.ComponentType>
> = {
  general: WorkspaceGeneralPage,
  features: FeaturesSettingsPage,
  profile: ProfileSettingsPage,
  'ai-providers': AISettingsPage,
  'mcp-servers': MCPServersSettingsPage,
  roles: RolesSettingsPage,
  security: SecuritySettingsPage,
  audit: AuditSettingsPage,
  encryption: EncryptionSettingsPage,
  'ai-governance': AIGovernanceSettingsPage,
  usage: UsageSettingsPage,
  sso: SsoSettingsPage,
  skills: SkillsSettingsPage,
  integrations: IntegrationsSettingsPage,
  billing: BillingPlaceholder as unknown as React.LazyExoticComponent<React.ComponentType>,
};

function PanelSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-[300px] w-full" />
    </div>
  );
}

export const SettingsModal = observer(function SettingsModal() {
  const { open, activeSection, closeSettings, setActiveSection } = useSettingsModal();
  const workspaceStore = useWorkspaceStore();
  const isGuest = workspaceStore.currentUserRole === 'guest';

  // Guests can only access profile
  const effectiveSection = isGuest && activeSection !== 'profile' ? 'profile' : activeSection;

  const ActiveComponent = SECTION_COMPONENTS[effectiveSection];

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && closeSettings()}>
      <DialogContent
        className="flex h-[85vh] max-h-[900px] w-full sm:max-w-5xl flex-col gap-0 overflow-hidden rounded-xl p-0"
        showCloseButton={false}
      >
        <DialogTitle className="sr-only">Settings</DialogTitle>

        <div className="flex h-full min-h-0 flex-col md:flex-row">
          {/* Sidebar — hidden below md, uses sidebar tokens for visual consistency */}
          <nav
            className="hidden w-48 shrink-0 border-r border-border bg-background-subtle md:flex md:flex-col"
            aria-label="Settings navigation"
          >
            {/* Sidebar header with icon */}
            <div className="flex h-12 items-center gap-2 border-b border-border px-4">
              <Settings className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-semibold text-foreground">Settings</span>
            </div>

            <ScrollArea className="flex-1 p-2">
              <div className="space-y-3">
                {settingsNavSections.map((section) => {
                  if (isGuest && section.label !== 'Account') return null;

                  return (
                    <div key={section.label}>
                      <p className="mb-0.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                        {section.label}
                      </p>
                      <ul className="space-y-px" role="list">
                        {section.items.map((item) => (
                          <li key={item.id}>
                            <button
                              onClick={() => setActiveSection(item.id)}
                              className={cn(
                                'flex w-full items-center gap-2 rounded-md px-2 py-2 text-[13px] font-medium transition-all duration-150 text-left',
                                'hover:bg-accent hover:text-accent-foreground',
                                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                                effectiveSection === item.id
                                  ? 'bg-accent text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]'
                                  : 'text-muted-foreground'
                              )}
                              aria-current={effectiveSection === item.id ? 'page' : undefined}
                            >
                              <item.icon
                                className={cn(
                                  'h-3.5 w-3.5 shrink-0 transition-colors',
                                  effectiveSection === item.id
                                    ? 'text-foreground'
                                    : 'text-muted-foreground/70'
                                )}
                              />
                              {item.label}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </nav>

          {/* Mobile header + section selector (shown below md) */}
          <div className="flex items-center gap-2 border-b border-border px-4 py-3 md:hidden">
            <Settings className="h-4 w-4 shrink-0 text-muted-foreground" />
            <select
              value={effectiveSection}
              onChange={(e) => setActiveSection(e.target.value as SettingsSection)}
              className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Settings section"
            >
              {settingsNavSections
                .filter((s) => !isGuest || s.label === 'Account')
                .map((section) => (
                  <optgroup key={section.label} label={section.label}>
                    {section.items.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
            </select>
            <button
              onClick={closeSettings}
              className="flex items-center justify-center rounded-md min-h-[44px] min-w-[44px] p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              aria-label="Close settings"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Content area with close button */}
          <div className="relative flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
            {/* Desktop close button — positioned inside content area */}
            <button
              onClick={closeSettings}
              className="absolute right-3 top-3 z-10 hidden rounded-md min-h-[44px] min-w-[44px] p-2.5 text-muted-foreground/60 hover:bg-accent hover:text-foreground transition-colors md:flex items-center justify-center"
              aria-label="Close settings"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Scrollable content with keyed transition */}
            <div className="flex-1 min-h-0 overflow-y-auto">
              <div key={effectiveSection} className="animate-in fade-in duration-150">
                <Suspense fallback={<PanelSkeleton />}>
                  <ActiveComponent />
                </Suspense>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
});
