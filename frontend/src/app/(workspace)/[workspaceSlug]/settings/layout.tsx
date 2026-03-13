/**
 * Shared settings layout with sidebar navigation.
 *
 * Provides consistent sidebar + content area for all settings sub-routes:
 * General (/settings), Profile (/settings/profile),
 * AI Providers (/settings/ai-providers), Integrations (/settings/integrations).
 * Members migrated to top-level /members route.
 */

'use client';

import * as React from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useWorkspaceStore } from '@/stores/RootStore';
import {
  BarChart3,
  Building2,
  ClipboardList,
  CreditCard,
  KeyRound,
  Menu,
  Plug,
  ServerCog,
  Settings,
  Shield,
  ShieldCheck,
  Sparkles,
  User,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  href: (slug: string) => string;
  /** Exact match only (for the default /settings route) */
  exact?: boolean;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const settingsNavSections: NavSection[] = [
  {
    label: 'Workspace',
    items: [
      {
        id: 'general',
        label: 'General',
        icon: Building2,
        href: (slug: string) => `/${slug}/settings`,
        exact: true,
      },
      {
        id: 'ai-providers',
        label: 'AI Providers',
        icon: Sparkles,
        href: (slug: string) => `/${slug}/settings/ai-providers`,
      },
      {
        id: 'mcp-servers',
        label: 'MCP Servers',
        icon: ServerCog,
        href: (slug: string) => `/${slug}/settings/mcp-servers`,
      },
      {
        id: 'integrations',
        label: 'Integrations',
        icon: Plug,
        href: (slug: string) => `/${slug}/settings/integrations`,
      },
      {
        id: 'sso',
        label: 'SSO',
        icon: Shield,
        href: (slug: string) => `/${slug}/settings/sso`,
      },
      {
        id: 'encryption',
        label: 'Encryption',
        icon: KeyRound,
        href: (slug: string) => `/${slug}/settings/encryption`,
      },
      {
        id: 'ai-governance',
        label: 'AI Governance',
        icon: ShieldCheck,
        href: (slug: string) => `/${slug}/settings/ai-governance`,
      },
      {
        id: 'audit',
        label: 'Audit',
        icon: ClipboardList,
        href: (slug: string) => `/${slug}/settings/audit`,
      },
      {
        id: 'roles',
        label: 'Custom Roles',
        icon: Users,
        href: (slug: string) => `/${slug}/settings/roles`,
      },
      {
        id: 'usage',
        label: 'Usage',
        icon: BarChart3,
        href: (slug: string) => `/${slug}/settings/usage`,
      },
      {
        id: 'billing',
        label: 'Billing',
        icon: CreditCard,
        href: (slug: string) => `/${slug}/settings/billing`,
      },
    ],
  },
  {
    label: 'Account',
    items: [
      {
        id: 'profile',
        label: 'Profile',
        icon: User,
        href: (slug: string) => `/${slug}/settings/profile`,
      },
    ],
  },
];

function isNavItemActive(pathname: string, href: string, exact?: boolean): boolean {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function SettingsNavContent({
  workspaceSlug,
  pathname,
  onNavClick,
}: {
  workspaceSlug: string;
  pathname: string;
  onNavClick?: () => void;
}) {
  return (
    <div className="space-y-4">
      {settingsNavSections.map((section) => (
        <div key={section.label}>
          <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
            {section.label}
          </p>
          <ul className="space-y-0.5" role="list">
            {section.items.map((item) => {
              const href = item.href(workspaceSlug);
              const isActive = isNavItemActive(pathname, href, item.exact);

              return (
                <li key={item.id}>
                  <Link
                    href={href}
                    onClick={onNavClick}
                    className={cn(
                      'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      'hover:bg-muted hover:text-foreground',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      isActive ? 'bg-muted text-foreground' : 'text-muted-foreground'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const workspaceStore = useWorkspaceStore();

  // Guests may only access their profile settings
  React.useEffect(() => {
    if (workspaceStore.currentUserRole === 'guest' && !pathname.includes('/settings/profile')) {
      router.replace(`/${workspaceSlug}/settings/profile`);
    }
  }, [workspaceStore.currentUserRole, pathname, workspaceSlug, router]);

  return (
    <div className="flex h-full flex-col">
      {/* Desktop Header — only visible at lg+ (tablet uses sheet nav, too tight with icon-rail) */}
      <div className="hidden border-b border-border px-6 py-4 lg:block">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Settings className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage your workspace preferences</p>
          </div>
        </div>
      </div>

      {/* Mobile/Tablet Header with Sheet trigger — visible below lg (md uses sheet since icon-rail takes space) */}
      <div className="flex items-center gap-4 border-b border-border px-4 py-4 lg:hidden">
        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-9 w-9 p-0"
              aria-label="Open settings navigation"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-4">
            <div className="flex items-center gap-2 mb-6">
              <Settings className="h-5 w-5 text-muted-foreground" />
              <span className="text-lg font-semibold">Settings</span>
            </div>
            <SettingsNavContent
              workspaceSlug={workspaceSlug}
              pathname={pathname}
              onNavClick={() => setMobileNavOpen(false)}
            />
          </SheetContent>
        </Sheet>
        <h1 className="text-lg font-semibold text-foreground">Settings</h1>
      </div>

      {/* Layout: Sidebar + Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Desktop Sidebar Navigation — only at lg+ so tablet gets full-width content */}
        <nav
          className="hidden w-56 shrink-0 border-r border-border overflow-y-auto p-3 lg:block"
          aria-label="Settings navigation"
        >
          <SettingsNavContent workspaceSlug={workspaceSlug} pathname={pathname} />
        </nav>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
