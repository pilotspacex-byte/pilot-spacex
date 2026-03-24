/**
 * Suppress known TipTap + React 19 warnings that crash Next.js dev overlay.
 *
 * TipTap v3's ReactRenderer calls flushSync during React's render lifecycle
 * to synchronously render NodeView portals. React 19 logs a console.error
 * for this, and Next.js dev overlay intercepts it as a hard crash → page reload.
 *
 * This also catches the ProseMirror RangeError from selectClickedLeaf when
 * clicking atom NodeViews after document changes.
 *
 * This is a development-only workaround until TipTap fixes:
 * https://github.com/ueberdosis/tiptap/issues/3580
 */

if (typeof window !== 'undefined') {
  // Suppress flushSync console.error from TipTap's ReactRenderer
  const origConsoleError = console.error;
  console.error = (...args: unknown[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('flushSync was called from inside a lifecycle method')
    ) {
      return; // Swallow — TipTap's ReactRenderer calls flushSync during render
    }
    origConsoleError.apply(console, args);
  };

  // Catch ProseMirror RangeError from selectClickedLeaf on atom NodeViews
  window.addEventListener('error', (event) => {
    if (
      event.error instanceof RangeError &&
      event.error.message.includes('Selection passed to setSelection')
    ) {
      event.preventDefault(); // Prevent Next.js error overlay from catching it
    }
  });
}
