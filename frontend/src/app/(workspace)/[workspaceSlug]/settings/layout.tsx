/**
 * Settings layout — redirect bridge.
 *
 * Settings now live in a modal (SettingsModal). When users navigate to
 * /settings/* directly (e.g. bookmark, deep link), this layout opens the
 * modal on the correct section and redirects back to the workspace root.
 */

'use client';

import * as React from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import type { SettingsSection } from '@/features/settings/settings-modal-context';

/** Map URL segment to modal section ID. */
function pathnameToSection(pathname: string): SettingsSection {
  const segments = pathname.split('/');
  // pathname: /{slug}/settings/{section}
  const section = segments[3]; // after '', slug, 'settings'
  const valid: SettingsSection[] = [
    'general',
    'ai-providers',
    'mcp-servers',
    'integrations',
    'sso',
    'encryption',
    'ai-governance',
    'audit',
    'roles',
    'usage',
    'billing',
    'profile',
    'skills',
    'security',
  ];
  if (section && valid.includes(section as SettingsSection)) {
    return section as SettingsSection;
  }
  return 'general';
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return <SettingsRedirectBridge>{children}</SettingsRedirectBridge>;
}

function SettingsRedirectBridge({ children: _children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;
  const { openSettings } = useSettingsModal();

  // When navigating to /settings/* directly, open the modal and redirect.
  // Return null to avoid mounting page children (prevents unnecessary data fetches / flash).
  React.useEffect(() => {
    const section = pathnameToSection(pathname);
    openSettings(section);
    router.replace(`/${workspaceSlug}`);
  }, [pathname, workspaceSlug, router, openSettings]);

  return null;
}
