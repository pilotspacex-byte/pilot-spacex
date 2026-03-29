/**
 * Individual skill card for marketplace browse grid.
 * Displays icon, name, author, description, rating, downloads, and category.
 * Source: Phase 055, P55-02
 */

'use client';

import {
  BarChart3,
  BookOpen,
  Code,
  Download,
  FileText,
  Palette,
  Shield,
  Star,
  Wand2,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import type { MarketplaceListingResponse } from '@/services/api/marketplace';

// ---------------------------------------------------------------------------
// Icon Lookup
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
  Download,
  Star,
};

function getIcon(name: string): LucideIcon {
  return ICON_MAP[name] ?? Wand2;
}

// ---------------------------------------------------------------------------
// Star Rating
// ---------------------------------------------------------------------------

function StarRating({ rating }: { rating: number | null | undefined }) {
  if (!rating) {
    return <span className="text-muted-foreground text-xs">No ratings</span>;
  }

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`h-3.5 w-3.5 ${
            i < Math.round(rating)
              ? 'fill-yellow-400 text-yellow-400'
              : 'text-muted-foreground/30'
          }`}
        />
      ))}
      <span className="text-muted-foreground ml-1 text-xs">
        {rating.toFixed(1)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SkillCardProps {
  listing: MarketplaceListingResponse;
  workspaceSlug: string;
}

export function SkillCard({ listing, workspaceSlug }: SkillCardProps) {
  const Icon = getIcon(listing.icon);

  return (
    <Link
      href={`/${workspaceSlug}/marketplace/${listing.id}`}
      className="block"
    >
      <Card className="hover:shadow-md h-full transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
              <Icon className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="line-clamp-2 text-sm font-semibold leading-tight">
                {listing.name}
              </h3>
              <p className="text-muted-foreground mt-0.5 text-xs">
                by {listing.author}
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pb-3">
          <p className="text-muted-foreground line-clamp-2 text-sm">
            {listing.description}
          </p>
        </CardContent>

        <CardFooter className="flex flex-wrap items-center gap-2 pt-0">
          <StarRating rating={listing.avgRating} />

          <div className="text-muted-foreground flex items-center gap-1 text-xs">
            <Download className="h-3 w-3" />
            {listing.downloadCount.toLocaleString()}
          </div>

          <Badge variant="secondary" className="ml-auto text-xs">
            {listing.category}
          </Badge>
        </CardFooter>
      </Card>
    </Link>
  );
}
