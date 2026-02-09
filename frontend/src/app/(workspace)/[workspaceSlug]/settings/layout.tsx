/**
 * Shared settings layout with sidebar navigation.
 *
 * Provides consistent sidebar + content area for all settings sub-routes:
 * General (/settings), Members (/settings/members), Profile (/settings/profile),
 * AI Providers (/settings/ai-providers), Integrations (/settings/integrations).
 */

'use client';

import * as React from 'react';
import { useParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Building2,
  CreditCard,
  Menu,
  Plug,
  Settings,
  Sparkles,
  User,
  Users,
  Wand2,
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
        id: 'members',
        label: 'Members',
        icon: Users,
        href: (slug: string) => `/${slug}/settings/members`,
      },
      {
        id: 'ai-providers',
        label: 'AI Providers',
        icon: Sparkles,
        href: (slug: string) => `/${slug}/settings/ai-providers`,
      },
      {
        id: 'integrations',
        label: 'Integrations',
        icon: Plug,
        href: (slug: string) => `/${slug}/settings/integrations`,
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
      {
        id: 'ai-providers',
        label: 'AI Providers',
        icon: Sparkles,
        href: (slug: string) => `/${slug}/settings/ai-providers`,
      },
      {
        id: 'skills',
        label: 'Skills',
        icon: Wand2,
        href: (slug: string) => `/${slug}/settings/skills`,
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
  const workspaceSlug = params?.workspaceSlug as string;
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  return (
    <div className="flex h-full flex-col">
      {/* Desktop Header */}
      <div className="hidden border-b border-border px-6 py-4 md:block">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <Settings className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage your workspace preferences</p>
          </div>
        </div>
      </div>

      {/* Mobile Header with Sheet trigger */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-3 md:hidden">
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
        {/* Desktop Sidebar Navigation */}
        <nav
          className="hidden w-56 shrink-0 border-r border-border overflow-y-auto p-3 md:block"
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
