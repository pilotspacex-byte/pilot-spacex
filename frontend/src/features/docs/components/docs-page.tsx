'use client';

import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { DocsSidebar } from './docs-sidebar';
import { DocsContent } from './docs-content';
import { TableOfContents } from './table-of-contents';
import { docsBySlug } from '../lib/docs-registry';
import type { TocHeading } from '../lib/markdown-headings';

interface DocsPageProps {
  slug: string;
  content: string;
  headings: TocHeading[];
}

export function DocsPage({ slug, content, headings }: DocsPageProps) {
  const doc = docsBySlug.get(slug);

  return (
    <div className="flex h-full">
      <DocsSidebar className="hidden lg:block" />

      <div className="flex flex-1 flex-col overflow-y-auto">
        {/* Mobile nav — visible below lg */}
        <div className="flex items-center border-b border-border px-4 py-2 lg:hidden">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                <Menu className="h-4 w-4" />
                <span className="text-sm">Docs navigation</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <DocsSidebar />
            </SheetContent>
          </Sheet>
        </div>

        <div className="flex flex-1">
          <main className="flex-1 px-8 py-6 lg:px-12">
            {doc && (
              <div className="mb-6 border-b border-border pb-4">
                <h1 className="text-2xl font-bold text-foreground">{doc.title}</h1>
                <p className="mt-1 text-sm text-muted-foreground">{doc.description}</p>
              </div>
            )}
            <DocsContent content={content} />
          </main>

          <TableOfContents
            headings={headings}
            className="hidden xl:block border-l border-border p-4"
          />
        </div>
      </div>
    </div>
  );
}
