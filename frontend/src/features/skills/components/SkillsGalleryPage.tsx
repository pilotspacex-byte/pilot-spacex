/**
 * SkillsGalleryPage — Phase 91 Plan 03 Task 3.
 *
 * Top-level component mounted by `/{workspaceSlug}/skills/page.tsx`.
 * Renders the skills catalog as a 1/2/3/4-column responsive grid using the
 * Phase 85 unified ArtifactCard via SkillCard.
 *
 * UI-SPEC §Surface 1 — copy and state matrix:
 *   - isPending  → 6 ArtifactCardSkeleton density="full"
 *   - isError    → "Couldn't load skills." + Reload (calls
 *                   queryClient.invalidateQueries(['skills', 'catalog']))
 *   - empty      → "No skills yet." + "Skills are defined in your backend
 *                   templates."
 *   - data       → grid of SkillCard, click → router.push to detail
 */
'use client';

import { useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ArtifactCardSkeleton } from '@/components/artifacts/ArtifactCardSkeleton';
import { Button } from '@/components/ui/button';
import { useSkillCatalog, SKILLS_CATALOG_QUERY_KEY } from '../hooks';
import { SkillCard } from './SkillCard';

export function SkillsGalleryPage() {
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceSlug = params?.workspaceSlug ?? '';
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isPending, isError } = useSkillCatalog();

  const onSelectSkill = useCallback(
    (slug: string) => router.push(`/${workspaceSlug}/skills/${slug}`),
    [router, workspaceSlug],
  );

  const onReload = useCallback(
    () =>
      queryClient.invalidateQueries({
        queryKey: SKILLS_CATALOG_QUERY_KEY,
      }),
    [queryClient],
  );

  return (
    <main className="mx-auto w-full max-w-screen-2xl px-4 py-6">
      <header className="sticky top-0 z-10 -mx-4 mb-4 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <h1 className="text-[15px] font-semibold text-foreground">Skills</h1>
          {data && data.length > 0 && (
            <span
              data-testid="skills-count-badge"
              className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] font-semibold text-muted-foreground"
            >
              {data.length}
            </span>
          )}
        </div>
      </header>

      {isPending ? (
        <ul
          aria-label="Loading skills"
          className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <li key={i}>
              <ArtifactCardSkeleton density="full" />
            </li>
          ))}
        </ul>
      ) : isError ? (
        <div role="alert" className="flex flex-col items-start gap-3 py-12">
          <p className="text-[13px] font-semibold text-foreground">
            Couldn&apos;t load skills.
          </p>
          <Button
            variant="link"
            onClick={onReload}
            className="px-0 text-[#29a386]"
          >
            Reload
          </Button>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="flex flex-col items-start gap-2 py-12">
          <p className="text-[13px] font-semibold text-foreground">
            No skills yet.
          </p>
          <p className="text-[13px] font-medium text-muted-foreground">
            Skills are defined in your backend templates.
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.map((skill) => (
            <li key={skill.slug}>
              <SkillCard
                skill={skill}
                onClick={() => onSelectSkill(skill.slug)}
              />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
