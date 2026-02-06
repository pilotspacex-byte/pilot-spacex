'use client';

import { useState, type FormEvent } from 'react';
import { observer } from 'mobx-react-lite';
import { motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Compass, Github, Mail, Loader2, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { authStore } from '@/stores/AuthStore';

type AuthMode = 'login' | 'signup';

const LoginPage = observer(function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleEmailAuth = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!email || !password) {
      setLocalError('Please enter email and password');
      return;
    }

    if (mode === 'signup' && !name) {
      setLocalError('Please enter your name');
      return;
    }

    let success: boolean;
    if (mode === 'signup') {
      success = await authStore.signup(email, password, name);
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

  const toggleMode = () => {
    setMode(mode === 'login' ? 'signup' : 'login');
    setLocalError(null);
    authStore.clearError();
  };

  const error = localError || authStore.error;

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
            {mode === 'login'
              ? 'Sign in to start collaborating with AI'
              : 'Join Pilot Space to start collaborating'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleEmailAuth} className="space-y-4">
            {mode === 'signup' && (
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Your name"
                  className="h-11"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={authStore.isLoading}
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
                disabled={authStore.isLoading}
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
                  disabled={authStore.isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {mode === 'login' && (
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
                className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
                role="alert"
              >
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 shadow-warm-sm"
              disabled={authStore.isLoading}
            >
              {authStore.isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Mail className="mr-2 h-4 w-4" />
              )}
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>
          </form>

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
              disabled={authStore.isLoading}
            >
              <Github className="mr-2 h-4 w-4" />
              GitHub
            </Button>
          </div>

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

          <p className="text-center text-xs text-muted-foreground">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
});

export default LoginPage;
