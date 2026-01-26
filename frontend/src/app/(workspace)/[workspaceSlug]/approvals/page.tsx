import { ApprovalQueuePage } from '@/features/approvals/pages';

/**
 * Approval Queue Page Route
 *
 * Route: /[workspaceSlug]/approvals
 * Access: Workspace admins only
 * Purpose: Review and resolve pending AI approval requests
 */
export default function ApprovalsPage() {
  return <ApprovalQueuePage />;
}
