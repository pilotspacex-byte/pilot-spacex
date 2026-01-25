'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Compass } from 'lucide-react';

export default function CallbackPage() {
  const router = useRouter();

  useEffect(() => {
    // Handle OAuth callback
    // This will be replaced with actual Supabase auth handling
    const timer = setTimeout(() => {
      router.push('/');
    }, 2000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center space-y-4 text-center">
      <div className="relative">
        <div className="absolute inset-0 animate-ping">
          <Compass className="h-12 w-12 text-primary/30" />
        </div>
        <Compass className="h-12 w-12 text-primary animate-ai-pulse" />
      </div>
      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-foreground">Completing sign in...</h2>
        <p className="text-sm text-muted-foreground">You&apos;ll be redirected shortly</p>
      </div>
    </div>
  );
}
