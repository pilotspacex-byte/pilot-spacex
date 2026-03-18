'use client';

import { DocsSidebar } from './docs-sidebar';
import { DocsContent } from './docs-content';
import { TableOfContents } from './table-of-contents';
import { docsBySlug } from '../lib/docs-registry';

interface DocsPageProps {
  slug: string;
  content: string;
}

export function DocsPage({ slug, content }: DocsPageProps) {
  const doc = docsBySlug.get(slug);

  return (
    <div className="flex h-full">
      <DocsSidebar className="hidden lg:block" />

      <div className="flex flex-1 overflow-y-auto">
        <main className="flex-1 px-8 py-6 lg:px-12">
          {doc && (
            <div className="mb-6 border-b border-border pb-4">
              <h1 className="text-2xl font-bold text-foreground">{doc.title}</h1>
              <p className="mt-1 text-sm text-muted-foreground">{doc.description}</p>
            </div>
          )}
          <DocsContent content={content} />
        </main>

        <TableOfContents content={content} className="hidden xl:block border-l border-border p-4" />
      </div>
    </div>
  );
}
