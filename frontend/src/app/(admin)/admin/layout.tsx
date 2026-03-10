/**
 * AdminLayout — Minimal layout for /admin route group.
 *
 * No workspace sidebar, no MobX store providers, no workspace context.
 * Inherits root layout's <html>/<body> and global Providers (QueryClient,
 * ThemeProvider). Only applies admin-specific body styling.
 */
import type { ReactNode } from 'react';

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return <div className="min-h-screen bg-background font-sans antialiased">{children}</div>;
}
