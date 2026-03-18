/**
 * Docs Detail Route — renders a single documentation page from markdown.
 *
 * Route: /[workspaceSlug]/docs/[slug]
 * Content is loaded server-side from features/docs/content/{slug}.md.
 * Headings are extracted server-side to avoid double-parsing on the client.
 */

import { notFound } from 'next/navigation';
import path from 'node:path';
import fs from 'node:fs';
import { DocsPage, docsBySlug } from '@/features/docs';
import { extractHeadings } from '@/features/docs/lib/markdown-headings';

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

function loadMarkdownContent(file: string): string | null {
  const contentDir = path.join(process.cwd(), 'src', 'features', 'docs', 'content');
  const filePath = path.join(contentDir, `${file}.md`);

  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return null;
  }
}

export default async function DocsDetailPage({ params }: PageProps) {
  const { slug } = await params;

  const doc = docsBySlug.get(slug);
  if (!doc) {
    notFound();
  }

  const content = loadMarkdownContent(doc.file);
  if (!content) {
    notFound();
  }

  const headings = extractHeadings(content);

  return <DocsPage slug={slug} content={content} headings={headings} />;
}
