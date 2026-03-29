'use client';

/**
 * SkillDetailPage - Full skill detail page with hero, description, reviews, and versions.
 *
 * Layout: Back nav, hero section, description, graph preview badge, tabbed reviews/versions.
 * Uses TanStack Query hooks from use-marketplace.ts.
 *
 * Source: Phase 055, P55-03
 */

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  Network,
  Star,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStore } from '@/stores';
import {
  useMarketplaceListing,
  useMarketplaceReviews,
  useMarketplaceVersions,
} from '@/features/skills/hooks/use-marketplace';

import { InstallButton } from './InstallButton';
import { ReviewSection } from './ReviewSection';
import { VersionHistory } from './VersionHistory';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SkillDetailPageProps {
  listingId: string;
  workspaceSlug: string;
}

// ---------------------------------------------------------------------------
// Star Rating Display
// ---------------------------------------------------------------------------

function StarRating({ rating, size = 16 }: { rating: number; size?: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={i <= Math.round(rating) ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground/30'}
          size={size}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading Skeleton
// ---------------------------------------------------------------------------

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      {/* Back nav */}
      <Skeleton className="h-5 w-40" />

      {/* Hero */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <Skeleton className="h-16 w-16 rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-10 w-28" />
      </div>

      {/* Meta badges */}
      <div className="flex gap-2">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-6 w-24" />
      </div>

      {/* Description */}
      <div className="space-y-3">
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-4/5" />
        <Skeleton className="h-5 w-3/5" />
      </div>

      {/* Tabs */}
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Not Found
// ---------------------------------------------------------------------------

function SkillNotFound({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <p className="text-lg font-medium text-muted-foreground">Skill not found</p>
      <Button variant="link" onClick={onBack}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Marketplace
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Graph Preview Badge
// ---------------------------------------------------------------------------

function GraphPreviewBadge({ graphData }: { graphData: Record<string, unknown> }) {
  const nodes = Array.isArray(graphData.nodes) ? graphData.nodes.length : 0;
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-muted/50 px-4 py-3">
      <Network className="h-5 w-5 text-muted-foreground" />
      <div>
        <p className="text-sm font-medium">Graph-based skill</p>
        {nodes > 0 && (
          <p className="text-xs text-muted-foreground">{nodes} node{nodes !== 1 ? 's' : ''}</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const SkillDetailPage = observer(function SkillDetailPage({
  listingId,
  workspaceSlug,
}: SkillDetailPageProps) {
  const router = useRouter();
  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  const {
    data: listing,
    isLoading,
    isError,
  } = useMarketplaceListing(workspaceId, listingId);

  // Prefetch reviews and versions so tabs load instantly
  useMarketplaceReviews(workspaceId, listingId);
  useMarketplaceVersions(workspaceId, listingId);

  const handleBack = useCallback(() => {
    router.push(`/${workspaceSlug}/marketplace`);
  }, [router, workspaceSlug]);

  // -- Loading --
  if (isLoading) return <DetailSkeleton />;
  if (isError || !listing) return <SkillNotFound onBack={handleBack} />;

  return (
    <div className="mx-auto max-w-4xl space-y-8 overflow-y-auto p-6">
      {/* Back navigation */}
      <button
        onClick={handleBack}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Marketplace
      </button>

      {/* Hero section */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          {/* Icon placeholder - large */}
          <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary/10 text-2xl">
            {listing.icon || listing.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{listing.name}</h1>
            <p className="text-sm text-muted-foreground">by {listing.author}</p>
          </div>
        </div>
        <InstallButton listing={listing} workspaceId={workspaceId} />
      </div>

      {/* Meta badges */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="secondary">{listing.category}</Badge>
        <Badge variant="outline">v{listing.version}</Badge>
        <span className="flex items-center gap-1 text-sm text-muted-foreground">
          <Download className="h-3.5 w-3.5" />
          {listing.downloadCount.toLocaleString()} installs
        </span>
        {listing.avgRating != null && listing.avgRating > 0 && (
          <span className="flex items-center gap-1.5">
            <StarRating rating={listing.avgRating} size={14} />
            <span className="text-sm text-muted-foreground">
              {listing.avgRating.toFixed(1)}
            </span>
          </span>
        )}
      </div>

      {/* Tags */}
      {listing.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {listing.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      <Separator />

      {/* Description */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Description</h2>
        <p className="text-muted-foreground leading-relaxed">
          {listing.description}
        </p>
        {listing.longDescription && (
          <div className="mt-4 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {listing.longDescription}
          </div>
        )}
      </section>

      {/* Graph preview */}
      {listing.graphData && (
        <GraphPreviewBadge graphData={listing.graphData} />
      )}

      <Separator />

      {/* Tabs: Reviews | Version History */}
      <Tabs defaultValue="reviews">
        <TabsList>
          <TabsTrigger value="reviews">Reviews</TabsTrigger>
          <TabsTrigger value="versions">Version History</TabsTrigger>
        </TabsList>

        <TabsContent value="reviews" className="mt-6">
          <ReviewSection listingId={listingId} workspaceId={workspaceId} />
        </TabsContent>

        <TabsContent value="versions" className="mt-6">
          <VersionHistory listingId={listingId} workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </div>
  );
});
