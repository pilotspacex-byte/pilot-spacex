/**
 * Docs Detail Route — renders a single documentation page from markdown.
 *
 * Route: /[workspaceSlug]/docs/[slug]
 * Content is loaded server-side from features/docs/content/{slug}.md
 */

import { notFound } from 'next/navigation';
import path from 'node:path';
import fs from 'node:fs';
import { DocsPage } from '@/features/docs';
import { docsBySlug } from '@/features/docs';

interface PageProps {
  params: Promise<{ workspaceSlug: string; slug: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  const doc = docsBySlug.get(slug);
  if (!doc) return { title: 'Not Found | Pilot Space' };

  return {
    title: `${doc.title} | Docs | Pilot Space`,
    description: doc.description,
  };
}

function loadMarkdownContent(slug: string): string | null {
  const contentDir = path.join(process.cwd(), 'src', 'features', 'docs', 'content');
  const filePath = path.join(contentDir, `${slug}.md`);

  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return null;
  }
}

export default async function DocsDetailPage({ params }: PageProps) {
  const { slug } = await params;

  if (!docsBySlug.has(slug)) {
    notFound();
  }

  const content = loadMarkdownContent(slug);
  if (!content) {
    notFound();
  }

  return <DocsPage slug={slug} content={content} />;
}
