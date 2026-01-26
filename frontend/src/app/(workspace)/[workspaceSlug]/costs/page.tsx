/**
 * AI Costs Route - Cost dashboard for workspace AI usage.
 *
 * Route: /[workspaceSlug]/costs
 * Access: Workspace admins only
 *
 * Displays:
 * - Cost summary cards
 * - Cost by agent chart
 * - Cost trends over time
 * - User cost breakdown table
 */

import { CostDashboardPage } from '@/features/costs/pages/cost-dashboard-page';

export const metadata = {
  title: 'AI Costs | Pilot Space',
  description: 'Monitor AI usage and costs across your workspace',
};

interface PageProps {
  params: {
    workspaceSlug: string;
  };
}

export default async function CostsPage({ params }: PageProps) {
  const { workspaceSlug } = params;

  // TODO: Fetch workspace ID from slug via API or server component
  // For now, using slug as ID (will be replaced with actual workspace lookup)
  const workspaceId = workspaceSlug;

  return <CostDashboardPage workspaceId={workspaceId} />;
}
