/**
 * Settings members redirect — migrated to top-level /members route.
 */

import { redirect } from 'next/navigation';

interface PageParams {
  workspaceSlug: string;
}

interface PageProps {
  params: Promise<PageParams>;
}

export default async function MembersSettingsRedirect({ params }: PageProps) {
  const { workspaceSlug } = await params;
  redirect(`/${workspaceSlug}/members`);
}
