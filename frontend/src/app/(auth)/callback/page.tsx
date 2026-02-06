'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Compass } from 'lucide-react';
import { supabase } from '@/lib/supabase';

export default function CallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error in URL hash (OAuth error flow)
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const errorParam = hashParams.get('error');
      const errorDescription = hashParams.get('error_description');

      if (errorParam) {
        setError(errorDescription || errorParam);
        setTimeout(() => {
          router.push(`/login?error=${encodeURIComponent(errorDescription || errorParam)}`);
        }, 2000);
        return;
      }

      // Supabase SDK with detectSessionInUrl: true auto-processes the hash.
      // Listen for the auth state change to confirm session is ready.
      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((event, session) => {
        if (event === 'SIGNED_IN' && session) {
          subscription.unsubscribe();
          router.push('/');
        }
        if (event === 'SIGNED_OUT' || (event === 'TOKEN_REFRESHED' && !session)) {
          subscription.unsubscribe();
          router.push('/login?error=Authentication+failed');
        }
      });

      // Also check if session is already available (fast path)
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) {
        setError(sessionError.message);
        subscription.unsubscribe();
        setTimeout(() => {
          router.push(`/login?error=${encodeURIComponent(sessionError.message)}`);
        }, 2000);
        return;
      }

      if (data.session) {
        subscription.unsubscribe();
        router.push('/');
        return;
      }

      // Timeout: if no session detected within 10 seconds, redirect to login
      const timeout = setTimeout(() => {
        subscription.unsubscribe();
        router.push('/login?error=Authentication+timed+out');
      }, 10000);

      return () => {
        clearTimeout(timeout);
        subscription.unsubscribe();
      };
    };

    handleCallback();
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
        {error ? (
          <>
            <h2 className="text-lg font-semibold text-destructive">Authentication failed</h2>
            <p className="text-sm text-muted-foreground">{error}</p>
            <p className="text-sm text-muted-foreground">Redirecting to login...</p>
          </>
        ) : (
          <>
            <h2 className="text-lg font-semibold text-foreground">Completing sign in...</h2>
            <p className="text-sm text-muted-foreground">You&apos;ll be redirected shortly</p>
          </>
        )}
      </div>
    </div>
  );
}
