'use client';

/**
 * MetadataPanel - Collapsible document metadata card.
 *
 * Shown above the tab list in FilePreviewModal for extractable file types.
 * Displays: document type icon, page count, language, file size, confidence badge.
 *
 * Feature 044: Artifact UI Enhancements (AUI-01)
 */
import * as React from 'react';
import { FileText, FileSpreadsheet, FileImage, Code2, ChevronDown, ChevronUp } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import type { ExtractionMetadata } from '@/types/attachments';

// Language code -> display name mapping
const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  zh: 'Chinese',
  fr: 'French',
  de: 'German',
  es: 'Spanish',
  ja: 'Japanese',
  ko: 'Korean',
  pt: 'Portuguese',
  ru: 'Russian',
  ar: 'Arabic',
};

function formatLanguage(code: string | null): string | null {
  if (!code) return null;
  return LANGUAGE_NAMES[code.toLowerCase()] ?? code.toUpperCase();
}

function formatPageCount(count: number | null): string | null {
  if (count === null) return null;
  return count === 1 ? '1 page' : `${count} pages`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Confidence badge
function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence === null) return null;
  const pct = Math.round(confidence * 100);
  const colorClass =
    pct >= 90
      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
      : pct >= 70
        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
  return (
    <span
      className={cn('inline-flex items-center rounded px-2 py-0.5 text-xs font-medium', colorClass)}
    >
      {pct}% confidence
    </span>
  );
}

// Document type icon
type DocType = 'pdf' | 'docx' | 'xlsx' | 'pptx' | 'image' | 'code' | 'unknown';

function getDocTypeFromMime(mimeType: string): DocType {
  if (mimeType === 'application/pdf') return 'pdf';
  if (mimeType.includes('wordprocessingml')) return 'docx';
  if (mimeType.includes('spreadsheetml')) return 'xlsx';
  if (mimeType.includes('presentationml')) return 'pptx';
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('text/')) return 'code';
  return 'unknown';
}

function DocTypeIcon({ mimeType, className }: { mimeType: string; className?: string }) {
  const docType = getDocTypeFromMime(mimeType);
  const iconClass = cn('size-4 shrink-0', className);
  switch (docType) {
    case 'xlsx':
      return <FileSpreadsheet className={iconClass} />;
    case 'image':
      return <FileImage className={iconClass} />;
    case 'code':
      return <Code2 className={iconClass} />;
    default:
      return <FileText className={iconClass} />;
  }
}

// MetadataPanel
export interface MetadataPanelProps {
  /** Extraction metadata from GET /ai/attachments/{id}/extraction */
  metadata: ExtractionMetadata;
  /** MIME type of the file - used to select the document type icon */
  mimeType: string;
  /** File size in bytes - displayed alongside other metadata */
  sizeBytes: number;
  /** Filename - shown in the collapsed header */
  filename: string;
  className?: string;
}

export function MetadataPanel({
  metadata,
  mimeType,
  sizeBytes,
  filename,
  className,
}: MetadataPanelProps) {
  const [open, setOpen] = React.useState(true);

  const pageCount = formatPageCount(metadata.pageCount);
  const language = formatLanguage(metadata.language);
  const fileSize = formatFileSize(sizeBytes);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className={cn('border-b', className)}>
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-muted/50 transition-colors"
          aria-label={open ? 'Collapse document metadata' : 'Expand document metadata'}
        >
          <DocTypeIcon mimeType={mimeType} className="text-muted-foreground" />
          <span className="flex-1 truncate text-left font-medium text-sm">{filename}</span>
          <ConfidenceBadge confidence={metadata.confidence} />
          {open ? (
            <ChevronUp className="size-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
          )}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 pb-2 text-xs text-muted-foreground">
          {pageCount && <span data-testid="metadata-page-count">{pageCount}</span>}
          {language && <span data-testid="metadata-language">{language}</span>}
          <span data-testid="metadata-file-size">{fileSize}</span>
          {metadata.wordCount !== null && (
            <span data-testid="metadata-word-count">
              {metadata.wordCount.toLocaleString()} words
            </span>
          )}
          {metadata.extractionSource !== 'none' && (
            <span data-testid="metadata-source">
              Extracted via{' '}
              {metadata.extractionSource === 'ocr'
                ? 'OCR'
                : metadata.extractionSource === 'raw'
                  ? 'Raw text'
                  : 'Office parser'}
            </span>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
