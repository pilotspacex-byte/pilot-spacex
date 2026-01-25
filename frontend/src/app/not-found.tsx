import Link from 'next/link';
import { Compass, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex max-w-md flex-col items-center space-y-6 px-4 text-center">
        <div className="relative">
          <div className="absolute inset-0 blur-2xl">
            <div className="h-24 w-24 rounded-full bg-muted" />
          </div>
          <div className="relative flex h-24 w-24 items-center justify-center rounded-2xl bg-muted">
            <Compass className="h-12 w-12 text-muted-foreground" strokeWidth={1.5} />
          </div>
        </div>
        <div className="space-y-2">
          <h1 className="text-4xl font-semibold text-foreground">404</h1>
          <p className="text-xl text-muted-foreground">Page not found</p>
          <p className="text-sm text-muted-foreground">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild className="gap-2">
            <Link href="/">
              <Home className="h-4 w-4" />
              Go home
            </Link>
          </Button>
          <Button variant="outline" asChild className="gap-2">
            <Link href="javascript:history.back()">
              <ArrowLeft className="h-4 w-4" />
              Go back
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
