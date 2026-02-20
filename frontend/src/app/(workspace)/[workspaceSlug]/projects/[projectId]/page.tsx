import { redirect } from 'next/navigation';

interface PageProps {
  params: Promise<{ workspaceSlug: string; projectId: string }>;
}

export default async function ProjectDetailPage({ params }: PageProps) {
  const { workspaceSlug, projectId } = await params;
  redirect(`/${workspaceSlug}/projects/${projectId}/overview`);
}
