/**
 * Marketplace Skill Detail Route.
 *
 * Route: /[workspaceSlug]/marketplace/[listingId]
 * Access: Workspace members
 *
 * Renders the full skill detail page with hero, description,
 * reviews, version history, and install/update flow.
 */

import { SkillDetailPage } from '@/features/skills/components/marketplace/SkillDetailPage';

export const metadata = {
  title: 'Skill Detail | Pilot Space',
  description: 'View skill details, reviews, and version history',
};

interface PageProps {
  params: {
    workspaceSlug: string;
    listingId: string;
  };
}

export default async function MarketplaceDetailPage({ params }: PageProps) {
  const { workspaceSlug, listingId } = params;

  return <SkillDetailPage listingId={listingId} workspaceSlug={workspaceSlug} />;
}
