'use client';

import { useEffect, useRef, useState } from 'react';
import type { Terminal } from '@xterm/xterm';
import type { FitAddon } from '@xterm/addon-fit';

/**
 * Custom hook managing the xterm.js Terminal instance and PTY session lifecycle.
 *
 * Dynamically imports xterm.js and all IPC wrappers (never at top level)
 * to prevent SSG build errors.
 *
 * The hook:
 * 1. Creates an xterm.js Terminal instance with 10,000-line scrollback
 * 2. Attaches FitAddon to auto-size xterm to its container
 * 3. Opens a PTY session via Tauri IPC
 * 4. Wires keyboard input (onData) to the PTY stdin
 * 5. Wires a ResizeObserver to keep PTY dimensions in sync
 * 6. Cleans up everything on unmount
 *
 * @param containerRef - Ref to the HTMLDivElement that xterm mounts into
 * @returns { isReady, sessionId } — isReady becomes true after the PTY session is created
 */
export function useTerminal(containerRef: React.RefObject<HTMLDivElement | null>): {
  isReady: boolean;
  sessionId: string | null;
} {
  // isReady and sessionId are user-facing state — they affect render output
  const [isReady, setIsReady] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Internal refs hold the live instances between renders without triggering re-renders
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let isCancelled = false;

    async function init() {
      if (!containerRef.current) return;

      // --- Dynamic imports (must NOT be top-level to prevent SSG errors) ---
      const { Terminal } = await import('@xterm/xterm');
      const { FitAddon } = await import('@xterm/addon-fit');
      // Import xterm CSS so the terminal renders correctly
      await import('@xterm/xterm/css/xterm.css');

      if (isCancelled || !containerRef.current) return;

      // --- Create xterm.js Terminal ---
      const term = new Terminal({
        scrollback: 10_000,
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace",
        theme: {
          background: '#1a1b26',
          foreground: '#c0caf5',
          cursor: '#c0caf5',
          selectionBackground: '#33467c',
        },
        cursorBlink: true,
        allowProposedApi: true,
      });

      // --- Attach FitAddon ---
      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);

      // --- Mount xterm into container ---
      term.open(containerRef.current);
      fitAddon.fit();

      termRef.current = term;
      fitAddonRef.current = fitAddon;

      const { rows, cols } = term;

      // --- Create PTY session via Tauri IPC ---
      const { createTerminal, writeTerminal, resizeTerminal } = await import('@/lib/tauri');

      if (isCancelled) {
        term.dispose();
        return;
      }

      const session = await createTerminal(rows, cols, (output) => {
        // Write batched PTY output to the xterm instance.
        // The Rust side batches at 16ms to prevent IPC flooding.
        term.write(output.data);
      });

      if (isCancelled) {
        // Session was created but component unmounted — clean it up
        const { closeTerminal } = await import('@/lib/tauri');
        void closeTerminal(session.session_id);
        term.dispose();
        return;
      }

      sessionIdRef.current = session.session_id;
      setSessionId(session.session_id);
      setIsReady(true);

      // --- Wire keyboard input to PTY stdin ---
      term.onData((data: string) => {
        // Fire-and-forget: keystroke forwarding is best-effort
        void writeTerminal(session.session_id, data);
      });

      // --- Wire ResizeObserver to keep PTY dimensions in sync ---
      // Pre-import resizeTerminal so the ResizeObserver callback (sync) can call it
      const resizeObs = new ResizeObserver(() => {
        if (!fitAddonRef.current || !termRef.current) return;
        fitAddonRef.current.fit();
        // Fire-and-forget: resize is best-effort, not critical
        void resizeTerminal(session.session_id, termRef.current.rows, termRef.current.cols);
      });

      if (containerRef.current) {
        resizeObs.observe(containerRef.current);
      }

      resizeObserverRef.current = resizeObs;
    }

    void init();

    return () => {
      isCancelled = true;

      // Cleanup: disconnect observer, close PTY session, dispose terminal
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }

      if (sessionIdRef.current) {
        const sid = sessionIdRef.current;
        sessionIdRef.current = null;
        // Fire-and-forget close — import is async but we don't await in cleanup
        import('@/lib/tauri').then(({ closeTerminal }) => {
          void closeTerminal(sid);
        });
      }

      if (termRef.current) {
        termRef.current.dispose();
        termRef.current = null;
      }

      fitAddonRef.current = null;
      setIsReady(false);
      setSessionId(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount — containerRef is stable (useRef)

  return { isReady, sessionId };
}
