/**
 * Featured skills carousel for marketplace hero section.
 * Pure CSS scroll-snap on mobile, static 3-col grid on desktop.
 * Source: Phase 055, P55-02
 */

'use client';

import {
  BarChart3,
  BookOpen,
  Code,
  FileText,
  Palette,
  Shield,
  Star,
  Wand2,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import type { MarketplaceListingResponse } from '@/services/api/marketplace';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, LucideIcon> = {
  Wand2,
  Code,
  FileText,
  Shield,
  Palette,
  BarChart3,
  BookOpen,
  Zap,
};

function getIcon(name: string): LucideIcon {
  return ICON_MAP[name] ?? Wand2;
}

const CATEGORY_GRADIENTS: Record<string, string> = {
  Development: 'from-blue-500/10 to-blue-600/5',
  Writing: 'from-emerald-500/10 to-emerald-600/5',
  Analysis: 'from-violet-500/10 to-violet-600/5',
  Documentation: 'from-amber-500/10 to-amber-600/5',
  Security: 'from-red-500/10 to-red-600/5',
  Design: 'from-pink-500/10 to-pink-600/5',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface FeaturedCarouselProps {
  listings: MarketplaceListingResponse[];
  workspaceSlug: string;
}

export function FeaturedCarousel({ listings, workspaceSlug }: FeaturedCarouselProps) {
  if (listings.length === 0) return null;

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Featured Skills</h2>
      <div className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 lg:grid lg:grid-cols-3 lg:overflow-visible">
        {listings.map((listing) => {
          const Icon = getIcon(listing.icon);
          const gradient = CATEGORY_GRADIENTS[listing.category] ?? 'from-gray-500/10 to-gray-600/5';

          return (
            <Link
              key={listing.id}
              href={`/${workspaceSlug}/marketplace/${listing.id}`}
              className="block min-w-[280px] snap-center lg:min-w-0"
            >
              <div
                className={`bg-gradient-to-br ${gradient} rounded-xl border p-6 transition-shadow hover:shadow-md`}
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="bg-background flex h-12 w-12 items-center justify-center rounded-lg shadow-sm">
                    <Icon className="text-primary h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold">{listing.name}</h3>
                    <p className="text-muted-foreground text-sm">
                      by {listing.author}
                    </p>
                  </div>
                </div>

                <p className="text-muted-foreground mb-4 line-clamp-2 text-sm">
                  {listing.description}
                </p>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    {listing.avgRating ? (
                      <>
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm font-medium">
                          {listing.avgRating.toFixed(1)}
                        </span>
                      </>
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        No ratings yet
                      </span>
                    )}
                  </div>
                  <Button size="sm" variant="secondary">
                    View Details
                  </Button>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
