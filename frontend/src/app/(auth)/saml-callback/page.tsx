'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Compass } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { apiClient } from '@/services/api';

/**
 * SAML callback page — handles the browser redirect from the backend SAML callback.
 *
 * Flow:
 * 1. Backend /auth/sso/saml/callback validates SAML assertion, provisions user,
 *    generates a magic link, and redirects here with ?token_hash=...&workspace_id=...
 * 2. This page calls supabase.auth.verifyOtp to exchange the token_hash for a JWT session.
 * 3. On success: optionally applies SSO role mapping, then redirects to /.
 * 4. On error: redirects to /login?error=saml_failed.
 */
export default function SamlCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  const tokenHash = searchParams.get('token_hash');
  const workspaceId = searchParams.get('workspace_id');

  useEffect(() => {
    const handleSamlCallback = async () => {
      // Guard: token_hash is required to exchange for a JWT session
      if (!tokenHash) {
        router.push('/login?error=saml_failed');
        return;
      }

      const { data, error: verifyError } = await supabase.auth.verifyOtp({
        token_hash: tokenHash,
        type: 'magiclink',
      });

      if (verifyError || !data.session) {
        setError(verifyError?.message ?? 'SAML session exchange failed');
        router.push('/login?error=saml_failed');
        return;
      }

      // Apply SSO role mapping claims if workspace_id is present (non-fatal)
      if (workspaceId) {
        try {
          const jwtClaims: Record<string, unknown> = {
            ...(data.session.user.app_metadata ?? {}),
            ...(data.session.user.user_metadata ?? {}),
          };
          await apiClient.post('/auth/sso/claim-role', {
            workspace_id: workspaceId,
            jwt_claims: jwtClaims,
          });
        } catch {
          // Non-fatal: unmapped claims default to "member"; proceed with login
        }
      }

      router.push('/');
    };

    handleSamlCallback();
  }, [router, tokenHash, workspaceId]);

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
            <h2 className="text-lg font-semibold text-foreground">Completing SSO sign in...</h2>
            <p className="text-sm text-muted-foreground">You&apos;ll be redirected shortly</p>
          </>
        )}
      </div>
    </div>
  );
}
