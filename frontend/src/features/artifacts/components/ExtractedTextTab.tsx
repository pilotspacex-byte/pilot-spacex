'use client';

/**
 * ExtractedTextTab - "Extracted Text" tab content for FilePreviewModal.
 *
 * Shows full OCR-extracted or Office-extracted text with layout preservation.
 * Tables within the extraction result are rendered via ExtractedTableView.
 *
 * Feature 044: Artifact UI Enhancements (AUI-02, AUI-03)
 */
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { ExtractedTableView } from './ExtractedTableView';
import type { AttachmentExtractionResult } from '@/types/attachments';

export interface ExtractedTextTabProps {
  /** Full extraction result from useExtractionResult hook */
  extraction: AttachmentExtractionResult | undefined;
  /** Whether the extraction query is currently loading */
  isLoading: boolean;
  className?: string;
}

export function ExtractedTextTab({ extraction, isLoading, className }: ExtractedTextTabProps) {
  if (isLoading) {
    return (
      <div className={cn('space-y-3 p-4', className)}>
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <p className="text-xs text-muted-foreground pt-2">
          Extraction in progress - check back shortly.
        </p>
      </div>
    );
  }

  if (!extraction || extraction.metadata.extractionSource === 'none') {
    return (
      <div
        className={cn('flex flex-col items-center justify-center gap-2 p-8 text-center', className)}
      >
        <p className="text-sm text-muted-foreground">No extraction available for this file type.</p>
        <p className="text-xs text-muted-foreground">
          Extraction is available for PDF, Office documents, and images.
        </p>
      </div>
    );
  }

  const { extractedText, tables, metadata } = extraction;
  const isOcr = metadata.extractionSource === 'ocr';

  return (
    <div className={cn('flex flex-col gap-4 p-4', className)}>
      {/* Full extracted text */}
      {extractedText && (
        <div>
          {isOcr ? (
            // OCR output: monospace layout-preserving rendering
            <pre
              className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground"
              data-testid="extracted-text-ocr"
            >
              {extractedText}
            </pre>
          ) : (
            // Office output: markdown-structured rendering
            <div data-testid="extracted-text-markdown" className="prose prose-sm max-w-none">
              {extractedText}
            </div>
          )}
        </div>
      )}

      {/* Extracted tables (if any) */}
      {tables.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground">
            Extracted Tables ({tables.length})
          </h3>
          {tables.map((tableMarkdown, i) => (
            <ExtractedTableView key={i} markdown={tableMarkdown} />
          ))}
        </div>
      )}

      {/* Provider attribution footer */}
      {metadata.providerName && (
        <p className="text-xs text-muted-foreground border-t pt-2 mt-2">
          Extraction powered by {metadata.providerName}
        </p>
      )}
    </div>
  );
}
