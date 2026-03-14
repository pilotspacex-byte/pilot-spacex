'use client';

import { useState, useEffect, type FormEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { motion } from 'motion/react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Compass, Github, Mail, Loader2, Eye, EyeOff, KeyRound, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { authStore, isAuthCoreMode } from '@/stores/AuthStore';
import { useWorkspaceSsoStatus, useSsoLogin } from '@/features/auth/hooks/use-sso-login';

type AuthMode = 'login' | 'signup';

/** Label shown on the SSO button based on OIDC provider name. */
function getSsoButtonLabel(
  hasSaml: boolean,
  hasOidc: boolean,
  oidcProvider: string | null
): string {
  if (hasOidc && oidcProvider) {
    const names: Record<string, string> = {
      google: 'Google',
      azure: 'Microsoft',
      okta: 'Okta',
    };
    const name = names[oidcProvider] ?? oidcProvider;
    return `Continue with ${name}`;
  }
  if (hasSaml) {
    return 'Continue with SSO';
  }
  return 'Continue with SSO';
}

const LoginPage = observer(function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);

  // workspace_id may be passed via query param (e.g. when redirected from a workspace login page)
  const workspaceId = searchParams.get('workspace_id');

  // Allowlist of known session error codes — prevents phishing via arbitrary query params
  const KNOWN_SESSION_ERRORS: Record<string, string> = {
    'Session expired. Please sign in again.': 'Session expired. Please sign in again.',
    session_expired: 'Session expired. Please sign in again.',
    unauthorized: 'You must sign in to access this page.',
  };
  const rawSessionError = searchParams.get('error');
  const sessionError = rawSessionError ? (KNOWN_SESSION_ERRORS[rawSessionError] ?? null) : null;

  useEffect(() => {
    setMounted(true);
  }, []);

  // Redirect authenticated users away from login page.
  // MobX observer() tracks authStore.isLoading/isAuthenticated reactively.
  useEffect(() => {
    if (!authStore.isLoading && authStore.isAuthenticated) {
      router.replace('/');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authStore.isLoading, authStore.isAuthenticated, router]);

  // Defer authStore.isLoading to post-mount to avoid hydration mismatch:
  // server singleton may have isLoading=false while client starts with isLoading=true
  const isAuthLoading = mounted && authStore.isLoading;

  const showNameField = mode === 'signup' && !isAuthCoreMode;

  // SSO status — only fetched when workspace_id is present in URL
  const { data: ssoStatus } = useWorkspaceSsoStatus(workspaceId);
  const initiateSsoLogin = useSsoLogin();

  const hasSso = !!(ssoStatus?.has_saml || ssoStatus?.has_oidc);
  const ssoRequired = !!ssoStatus?.sso_required;

  const handleEmailAuth = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!email || !password) {
      setLocalError('Please enter email and password');
      return;
    }

    if (showNameField && !name) {
      setLocalError('Please enter your name');
      return;
    }

    let success: boolean;
    if (mode === 'signup') {
      success = await authStore.signup(email, password, isAuthCoreMode ? undefined : name);
    } else {
      success = await authStore.login(email, password);
    }

    if (success) {
      router.push('/');
    }
  };

  const handleGitHubAuth = async () => {
    await authStore.loginWithOAuth('github');
  };

  const handleSsoLogin = async () => {
    if (!workspaceId) return;
    setSsoLoading(true);
    try {
      const method = ssoStatus?.has_oidc ? 'oidc' : 'saml';
      const oidcProvider = ssoStatus?.oidc_provider ?? undefined;
      await initiateSsoLogin(workspaceId, method, oidcProvider);
    } catch {
      setLocalError('SSO login failed. Please try again or contact your administrator.');
    } finally {
      setSsoLoading(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === 'login' ? 'signup' : 'login');
    setLocalError(null);
    authStore.clearError();
  };

  const error = sessionError || localError || authStore.error;

  const ssoButtonLabel = ssoStatus
    ? getSsoButtonLabel(ssoStatus.has_saml, ssoStatus.has_oidc, ssoStatus.oidc_provider)
    : 'Continue with SSO';

  // When sso_required=true, only render the SSO button (hide email/password form)
  const showEmailForm = !ssoRequired;
  const showSsoButton = hasSso && mode === 'login';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card className="shadow-warm-lg">
        <CardHeader className="text-center">
          <motion.div
            className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10"
            whileHover={{ rotate: 15 }}
            transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          >
            <Compass className="h-7 w-7 text-primary" />
          </motion.div>
          <CardTitle className="text-2xl">
            {mode === 'login' ? 'Welcome to Pilot Space' : 'Create your account'}
          </CardTitle>
          <CardDescription>
            {ssoRequired
              ? 'This workspace requires SSO login.'
              : mode === 'login'
                ? 'Sign in to start collaborating with AI'
                : 'Join Pilot Space to start collaborating'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* SSO button — shown above email form when SSO is available but not required */}
          {showSsoButton && (
            <>
              <Button
                type="button"
                variant={ssoRequired ? 'default' : 'outline'}
                className="w-full h-11"
                onClick={handleSsoLogin}
                disabled={ssoLoading || isAuthLoading}
                aria-label={ssoButtonLabel}
                data-testid="sso-login-button"
              >
                {ssoLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="mr-2 h-4 w-4" />
                )}
                {ssoButtonLabel}
              </Button>

              {/* Divider between SSO and email/password — only when both are shown */}
              {showEmailForm && (
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <Separator className="w-full" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">
                      Or sign in with email
                    </span>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Email/password form — hidden when sso_required=true */}
          {showEmailForm && (
            <form onSubmit={handleEmailAuth} className="space-y-4">
              {showNameField && (
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Your name"
                    className="h-11"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={isAuthLoading}
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Email address"
                  className="h-11"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isAuthLoading}
                  aria-describedby={error ? 'auth-error' : undefined}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Password"
                    className="h-11 pr-10"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isAuthLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {mode === 'login' && !isAuthCoreMode && (
                  <div className="flex justify-end">
                    <Link
                      href="/forgot-password"
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>
                )}
              </div>

              {error && (
                <div
                  id="auth-error"
                  className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive"
                  role="alert"
                >
                  <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                type="submit"
                className="w-full h-11 shadow-warm-sm"
                disabled={isAuthLoading}
                aria-busy={isAuthLoading}
              >
                {isAuthLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="mr-2 h-4 w-4" />
                )}
                {mode === 'login' ? 'Sign In' : 'Create Account'}
              </Button>
            </form>
          )}

          {/* SSO-required error message when sso_required=true */}
          {ssoRequired && error && (
            <div
              id="auth-error"
              className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {!isAuthCoreMode && showEmailForm && (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <Separator className="w-full" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2">
                <Button
                  variant="outline"
                  className="h-11"
                  onClick={handleGitHubAuth}
                  disabled={isAuthLoading}
                >
                  <Github className="mr-2 h-4 w-4" />
                  GitHub
                </Button>
              </div>
            </>
          )}

          {showEmailForm && (
            <div className="text-center text-sm">
              {mode === 'login' ? (
                <span className="text-muted-foreground">
                  Don&apos;t have an account?{' '}
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="font-medium text-primary hover:underline"
                  >
                    Sign up
                  </button>
                </span>
              ) : (
                <span className="text-muted-foreground">
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="font-medium text-primary hover:underline"
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>
          )}

          <p className="text-center text-xs text-muted-foreground">
            By continuing, you agree to our{' '}
            <a
              href="#"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-foreground"
            >
              Terms of Service
            </a>{' '}
            and{' '}
            <a
              href="#"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-foreground"
            >
              Privacy Policy
            </a>
            .
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
});

export default LoginPage;
