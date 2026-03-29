/**
 * Marketplace browse page - main entry for skill discovery.
 * Shows featured carousel, category grid, tabbed listings, and search.
 * Source: Phase 055, P55-02
 */

'use client';

import { useCallback, useState } from 'react';

import { observer } from 'mobx-react-lite';
import { Plus } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { MarketplaceSearchParams } from '@/services/api/marketplace';
import { useStore } from '@/stores';

import { useMarketplaceSearch } from '../../hooks/use-marketplace';

import { CategoryGrid } from './CategoryGrid';
import { FeaturedCarousel } from './FeaturedCarousel';
import { MarketplaceSearchBar } from './MarketplaceSearchBar';
import { SkillCard } from './SkillCard';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_PARAMS: MarketplaceSearchParams = {
  sort: 'popular',
  limit: 20,
  offset: 0,
};

type TabValue = 'trending' | 'popular' | 'new';

const TAB_SORT_MAP: Record<TabValue, MarketplaceSearchParams['sort']> = {
  trending: 'popular',
  popular: 'popular',
  new: 'newest',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const MarketplaceBrowsePage = observer(function MarketplaceBrowsePage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const [searchParams, setSearchParams] = useState<MarketplaceSearchParams>(DEFAULT_PARAMS);
  const [activeTab, setActiveTab] = useState<TabValue>('trending');

  const { data, isLoading } = useMarketplaceSearch(workspaceId, searchParams);

  // Whether the user is actively searching/filtering
  const isSearchActive = !!(searchParams.query || searchParams.category);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleSearchChange = useCallback(
    (partial: Partial<MarketplaceSearchParams>) => {
      setSearchParams((prev) => ({ ...prev, ...partial }));
    },
    [],
  );

  const handleTabChange = useCallback(
    (tab: string) => {
      const t = tab as TabValue;
      setActiveTab(t);
      setSearchParams((prev) => ({
        ...prev,
        sort: TAB_SORT_MAP[t],
        offset: 0,
      }));
    },
    [],
  );

  const handleCategorySelect = useCallback(
    (category: string) => {
      setSearchParams((prev) => ({
        ...prev,
        category,
        offset: 0,
      }));
    },
    [],
  );

  const handleLoadMore = useCallback(() => {
    setSearchParams((prev) => ({
      ...prev,
      offset: (prev.offset ?? 0) + (prev.limit ?? 20),
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Marketplace</h1>
          <p className="text-muted-foreground mt-2">
            Discover and install skills for your workspace
          </p>
        </div>
        <Button
          onClick={() => router.push(`/${workspaceSlug}/skills/generator`)}
          data-testid="create-publish-btn"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          Create &amp; Publish
        </Button>
      </div>

      {/* Search bar */}
      <div className="mb-8">
        <MarketplaceSearchBar
          onSearchChange={handleSearchChange}
          currentParams={searchParams}
        />
      </div>

      {/* Featured carousel - only when not searching */}
      {!isSearchActive && items.length > 0 && (
        <div className="mb-10">
          <FeaturedCarousel
            listings={items.slice(0, 3)}
            workspaceSlug={workspaceSlug}
          />
        </div>
      )}

      {/* Category grid - only when not searching */}
      {!isSearchActive && !searchParams.category && (
        <div className="mb-10">
          <h2 className="mb-4 text-lg font-semibold">Browse by Category</h2>
          <CategoryGrid onCategorySelect={handleCategorySelect} />
        </div>
      )}

      {/* Tabbed listings */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="trending">Trending</TabsTrigger>
          <TabsTrigger value="popular">Popular</TabsTrigger>
          <TabsTrigger value="new">New</TabsTrigger>
        </TabsList>

        {/* All tabs render the same grid, data changes via sort param */}
        {(['trending', 'popular', 'new'] as const).map((tab) => (
          <TabsContent key={tab} value={tab} className="mt-6">
            {/* Loading skeleton */}
            {isLoading && items.length === 0 && (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="space-y-3">
                    <Skeleton className="h-[200px] w-full rounded-lg" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                ))}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && items.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20">
                <p className="text-muted-foreground text-lg">No skills found</p>
                <p className="text-muted-foreground mt-1 text-sm">
                  Try adjusting your search or filters
                </p>
              </div>
            )}

            {/* Skill card grid */}
            {items.length > 0 && (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {items.map((listing) => (
                  <SkillCard
                    key={listing.id}
                    listing={listing}
                    workspaceSlug={workspaceSlug}
                  />
                ))}
              </div>
            )}

            {/* Load more */}
            {data?.hasNext && (
              <div className="mt-8 flex justify-center">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  disabled={isLoading}
                >
                  {isLoading ? 'Loading...' : 'Load More'}
                </Button>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
});
