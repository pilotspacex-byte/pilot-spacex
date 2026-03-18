/**
 * Docs Index Route — redirects to the default documentation page.
 *
 * Route: /[workspaceSlug]/docs
 */

import { redirect } from 'next/navigation';
import { defaultDocSlug } from '@/features/docs';

interface PageProps {
  params: Promise<{ workspaceSlug: string }>;
}

export default async function DocsIndexPage({ params }: PageProps) {
  const { workspaceSlug } = await params;
  redirect(`/${workspaceSlug}/docs/${defaultDocSlug}`);
}
