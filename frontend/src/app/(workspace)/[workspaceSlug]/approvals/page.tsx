/**
 * Approvals route — /[workspaceSlug]/approvals
 *
 * AIGOV-01: AI approval queue for workspace Owners/Admins.
 * Sidebar nav item routes here; badge shows pending count.
 */

import { ApprovalsPage } from '@/features/approvals/pages/approvals-page';

export default function ApprovalsRoute() {
  return <ApprovalsPage />;
}
