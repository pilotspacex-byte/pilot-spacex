import { Compass } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex flex-col items-center space-y-4">
        <div className="relative">
          <div className="absolute inset-0 animate-ping">
            <Compass className="h-12 w-12 text-primary/30" />
          </div>
          <Compass className="h-12 w-12 text-primary animate-ai-pulse" />
        </div>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}
