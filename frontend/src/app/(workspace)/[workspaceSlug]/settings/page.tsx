/**
 * Settings index page.
 *
 * T032: Renders WorkspaceGeneralPage as default settings view.
 * Sidebar navigation is provided by the shared settings layout.tsx.
 */

import { WorkspaceGeneralPage } from '@/features/settings/pages/workspace-general-page';

export default function SettingsPage() {
  return <WorkspaceGeneralPage />;
}
