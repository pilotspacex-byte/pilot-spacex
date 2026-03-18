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
  Shield,
  ShieldCheck,
  Sparkles,
  User,
  Users,
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

// Billing placeholder (inline — trivial component)
function BillingPlaceholder() {
  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-foreground">Billing</h2>
        <p className="text-sm text-muted-foreground">Manage your workspace plan and usage.</p>
      </div>
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <CreditCard className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-sm font-medium text-foreground">Billing coming soon</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Pilot Space is free and open source. Paid tiers for support SLAs will be available in a
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
        className="flex h-[85vh] max-h-[900px] w-full max-w-5xl flex-col gap-0 overflow-hidden p-0"
        showCloseButton
      >
        <DialogTitle className="sr-only">Settings</DialogTitle>
        <div className="flex h-full min-h-0">
          {/* Sidebar */}
          <nav
            className="hidden w-52 shrink-0 border-r border-border bg-muted/30 md:block"
            aria-label="Settings navigation"
          >
            <ScrollArea className="h-full p-3">
              <div className="space-y-4">
                {settingsNavSections.map((section) => {
                  // Guests only see Account section
                  if (isGuest && section.label !== 'Account') return null;

                  return (
                    <div key={section.label}>
                      <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                        {section.label}
                      </p>
                      <ul className="space-y-0.5" role="list">
                        {section.items.map((item) => (
                          <li key={item.id}>
                            <button
                              onClick={() => setActiveSection(item.id)}
                              className={cn(
                                'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
                                'hover:bg-muted hover:text-foreground',
                                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                                effectiveSection === item.id
                                  ? 'bg-muted text-foreground'
                                  : 'text-muted-foreground'
                              )}
                              aria-current={effectiveSection === item.id ? 'page' : undefined}
                            >
                              <item.icon className="h-4 w-4 shrink-0" />
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

          {/* Mobile section selector (shown below md) */}
          <div className="border-b border-border p-3 md:hidden">
            <select
              value={effectiveSection}
              onChange={(e) => setActiveSection(e.target.value as SettingsSection)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              aria-label="Settings section"
            >
              {settingsNavSections
                .filter((s) => !isGuest || s.label === 'Account')
                .flatMap((s) => s.items)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
            </select>
          </div>

          {/* Content area */}
          <div className="flex-1 min-w-0 overflow-y-auto">
            <Suspense fallback={<PanelSkeleton />}>
              <ActiveComponent />
            </Suspense>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
});
