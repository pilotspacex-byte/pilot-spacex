import { useState, useRef, useEffect, useCallback } from 'react';

interface UseCopyFeedbackReturn {
  copied: boolean;
  handleCopy: (copyFn: () => Promise<boolean>) => Promise<void>;
}

/**
 * Manages copy-to-clipboard feedback state with auto-reset.
 *
 * Provides a `copied` boolean that flips to true for 2 seconds after
 * a successful copy, plus cleanup on unmount to prevent memory leaks.
 *
 * @example
 * ```tsx
 * const { copied, handleCopy } = useCopyFeedback();
 * <Button onClick={() => handleCopy(() => copyToClipboard(text))}>
 *   {copied ? 'Copied!' : 'Copy'}
 * </Button>
 * ```
 */
export function useCopyFeedback(): UseCopyFeedbackReturn {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const handleCopy = useCallback(async (copyFn: () => Promise<boolean>) => {
    const success = await copyFn();
    if (success) {
      setCopied(true);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  return { copied, handleCopy };
}
