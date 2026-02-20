'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface ProjectCardSkeletonProps {
  variant?: 'grid' | 'list';
}

export function ProjectCardSkeleton({ variant = 'grid' }: ProjectCardSkeletonProps) {
  if (variant === 'list') {
    return (
      <Card>
        <div className="flex items-center gap-4 px-4 py-3">
          <Skeleton className="h-8 w-8 rounded-lg flex-shrink-0" />
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-48 hidden md:block" />
          <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
          <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
          <Skeleton className="h-4 w-16 hidden sm:block" />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div>
              <Skeleton className="h-3 w-10 mb-1" />
              <Skeleton className="h-5 w-28" />
            </div>
          </div>
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-2/3 mb-3" />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded-full" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-3 w-14" />
        </div>
      </CardContent>
    </Card>
  );
}
