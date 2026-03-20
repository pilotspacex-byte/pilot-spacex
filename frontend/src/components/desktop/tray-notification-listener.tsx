'use client';

import { useEffect } from 'react';
import { isTauri } from '@/lib/tauri';

/**
 * Listens for 'implement-complete' DOM events dispatched by ImplementStore and
 * fires a native OS notification via the Rust send_notification IPC command.
 *
 * This component is intentionally NOT wrapped in observer() — it consumes no
 * MobX observables. It mounts once and manages its own DOM event listener.
 *
 * Renders nothing (returns null). Mount in a persistent layout so the listener
 * survives client-side navigation.
 */
export function TrayNotificationListener() {
  useEffect(() => {
    if (!isTauri()) return;

    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        issueId: string;
        success: boolean;
        error?: string;
      };

      const { sendNotification } = await import('@/lib/tauri');

      if (detail.success) {
        await sendNotification(
          'Implement Complete',
          `Successfully implemented ${detail.issueId} and pushed to remote.`
        );
      } else {
        await sendNotification(
          'Implement Failed',
          `Failed to implement ${detail.issueId}: ${detail.error ?? 'Unknown error'}`
        );
      }
    };

    window.addEventListener('implement-complete', handler);
    return () => window.removeEventListener('implement-complete', handler);
  }, []);

  return null;
}
