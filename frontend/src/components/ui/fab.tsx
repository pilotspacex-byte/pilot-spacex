'use client';

/**
 * FAB (Floating Action Button) - AI Quick Search
 * A floating button in the bottom-right corner for quick AI search access
 * Based on prototype v4 design
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, X, FileText, Bug, Lightbulb, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

export interface FABProps {
  /** Callback when search is submitted */
  onSearch?: (query: string) => void;
  /** Whether FAB is disabled */
  disabled?: boolean;
  /** Custom class name */
  className?: string;
}

interface SearchResult {
  id: string;
  type: 'note' | 'issue' | 'suggestion';
  title: string;
  snippet?: string;
  meta?: string;
}

// Mock results for demonstration
const mockResults: SearchResult[] = [
  {
    id: '1',
    type: 'note',
    title: 'Sprint Planning Notes',
    snippet: 'Key decisions from our planning session...',
    meta: 'Updated 2 hours ago',
  },
  {
    id: '2',
    type: 'issue',
    title: 'Fix authentication timeout',
    snippet: 'Users are experiencing session timeouts...',
    meta: 'PS-142 • In Progress',
  },
  {
    id: '3',
    type: 'suggestion',
    title: 'Consider adding rate limiting',
    snippet: 'AI suggestion based on your API design...',
    meta: 'AI Suggestion',
  },
];

const typeIcons = {
  note: FileText,
  issue: Bug,
  suggestion: Lightbulb,
};

/**
 * FAB Component - Floating Action Button for AI Quick Search
 */
export function FAB({ onSearch, disabled = false, className }: FABProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when search opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle search
  const handleSearch = useCallback((searchQuery: string) => {
    setQuery(searchQuery);
    if (searchQuery.trim().length > 0) {
      setIsSearching(true);
      // Simulate search delay
      setTimeout(() => {
        setResults(
          mockResults.filter(
            (r) =>
              r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
              r.snippet?.toLowerCase().includes(searchQuery.toLowerCase())
          )
        );
        setIsSearching(false);
      }, 300);
    } else {
      setResults([]);
    }
  }, []);

  // Handle submit
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (query.trim() && onSearch) {
        onSearch(query.trim());
      }
    },
    [query, onSearch]
  );

  // Close search
  const handleClose = useCallback(() => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
  }, []);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleClose]);

  return (
    <>
      {/* FAB Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            onClick={() => setIsOpen(true)}
            disabled={disabled}
            className={cn(
              'fixed bottom-20 right-6 z-50',
              'w-14 h-14 rounded-full',
              'bg-ai text-ai-foreground',
              'flex items-center justify-center',
              'shadow-warm-lg hover:shadow-warm-xl',
              'transition-all duration-200',
              'hover:scale-105 active:scale-95',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'focus:outline-none focus:ring-2 focus:ring-ai/50 focus:ring-offset-2',
              className
            )}
            aria-label="Open AI search"
          >
            <Sparkles className="h-6 w-6" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Search Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-40 bg-foreground/10 backdrop-blur-sm"
              onClick={handleClose}
            />

            {/* Search Panel */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className={cn(
                'fixed bottom-20 right-6 z-50',
                'w-[400px] max-w-[calc(100vw-3rem)]',
                'bg-background border border-border',
                'rounded-2xl shadow-warm-xl overflow-hidden'
              )}
            >
              {/* Search Input */}
              <form
                onSubmit={handleSubmit}
                className="flex items-center gap-3 p-4 border-b border-border"
              >
                <Sparkles className="h-5 w-5 text-ai flex-shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Ask AI anything..."
                  className={cn(
                    'flex-1 bg-transparent text-foreground',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none',
                    'text-base'
                  )}
                />
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </form>

              {/* AI Answer Section */}
              {query.trim().length > 0 && (
                <div className="p-4 bg-ai-muted border-b border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="h-4 w-4 text-ai" />
                    <span className="text-xs font-semibold text-ai uppercase tracking-wide">
                      AI Answer
                    </span>
                  </div>
                  {isSearching ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="animate-spin h-4 w-4 border-2 border-ai border-t-transparent rounded-full" />
                      Thinking...
                    </div>
                  ) : (
                    <>
                      <p className="text-sm text-foreground leading-relaxed">
                        Based on your notes and issues, I found relevant information about{' '}
                        <strong>{query}</strong>. Here are some related items that might help.
                      </p>
                      <div className="flex gap-2 mt-3">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs border-ai-border text-ai hover:bg-ai hover:text-ai-foreground"
                        >
                          Create Topic
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs border-ai-border text-ai hover:bg-ai hover:text-ai-foreground"
                        >
                          Create Task
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Search Results */}
              <div className="max-h-[300px] overflow-y-auto">
                {results.length > 0 ? (
                  results.map((result) => {
                    const Icon = typeIcons[result.type];
                    return (
                      <button
                        key={result.id}
                        className={cn(
                          'w-full flex items-start gap-3 p-4',
                          'text-left transition-colors',
                          'hover:bg-muted focus:bg-muted focus:outline-none'
                        )}
                      >
                        <Icon className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-foreground truncate">
                            {result.title}
                          </div>
                          {result.snippet && (
                            <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                              {result.snippet}
                            </div>
                          )}
                          {result.meta && (
                            <div className="text-xs text-muted-foreground mt-1">{result.meta}</div>
                          )}
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      </button>
                    );
                  })
                ) : query.trim().length > 0 && !isSearching ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No results found for &ldquo;{query}&rdquo;
                  </div>
                ) : (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    Start typing to search...
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-3 border-t border-border bg-muted/30">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    Press{' '}
                    <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">Esc</kbd>{' '}
                    to close
                  </span>
                  <span>
                    <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">
                      Enter
                    </kbd>{' '}
                    to search
                  </span>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export default FAB;
