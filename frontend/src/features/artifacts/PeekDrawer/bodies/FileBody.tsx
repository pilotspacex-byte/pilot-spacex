'use client';

/**
 * FileBody — file-artifact preview inside the PeekDrawer.
 *
 * Reuses lazy renderers from FilePreviewModal. The drawer variant omits
 * annotations (those live in the full preview).
 *
 * API gap: the current artifact APIs require `{workspaceId, projectId,
 * artifactId}` for signed URLs AND the signed-URL response returns only
 * `{url, expiresAt}` — filename / mimeType / sizeBytes must come from a
 * separate list call (`artifactsApi.list`).
 *
 * For that reason this body only renders previews when BOTH of the following
 * hold:
 *   - `projectId` is available on the current Next.js route params
 *   - the artifact is found in the project's artifact list cache
 *
 * When either is missing (e.g. deep-linked peek from the homepage) the body
 * shows a "context missing" fallback pointing to the full preview surface.
 * Removing this gap requires a new backend endpoint that resolves an artifact
 * by ID alone (documented in the migration plan).
 */

import * as React from 'react';
import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import { AlertTriangle, Download } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { useWorkspace } from '@/components/workspace-guard';
import { artifactsApi } from '@/services/api/artifacts';
import { useArtifactSignedUrl } from '../../hooks/use-artifact-signed-url';
import { useFileContent } from '../../hooks/useFileContent';
import { resolveRenderer, getLanguageForFile } from '../../utils/mime-type-router';
import { CodeSkeleton, ProseSkeleton, TableSkeleton } from '../../components/preview-skeletons';
import type { ArtifactType } from '../../ArtifactCard';

const MarkdownRenderer = dynamic(
  () =>
    import('../../components/renderers/MarkdownRenderer').then((m) => ({
      default: m.MarkdownRenderer,
    })),
  { loading: () => <ProseSkeleton /> }
);
const TextRenderer = dynamic(
  () => import('../../components/renderers/TextRenderer').then((m) => ({ default: m.TextRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const JsonRenderer = dynamic(
  () => import('../../components/renderers/JsonRenderer').then((m) => ({ default: m.JsonRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const CodeRenderer = dynamic(
  () => import('../../components/renderers/CodeRenderer').then((m) => ({ default: m.CodeRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const CsvRenderer = dynamic(
  () => import('../../components/renderers/CsvRenderer').then((m) => ({ default: m.CsvRenderer })),
  { loading: () => <TableSkeleton /> }
);
const HtmlRenderer = dynamic(
  () => import('../../components/renderers/HtmlRenderer').then((m) => ({ default: m.HtmlRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const ImageRenderer = dynamic(
  () =>
    import('../../components/renderers/ImageRenderer').then((m) => ({ default: m.ImageRenderer })),
  { ssr: false }
);
const DocxRenderer = dynamic(
  () => import('../../components/renderers/DocxRenderer').then((m) => ({ default: m.DocxRenderer })),
  { ssr: false }
);
const XlsxRenderer = dynamic(
  () => import('../../components/renderers/XlsxRenderer').then((m) => ({ default: m.XlsxRenderer })),
  { ssr: false }
);
const PptxRenderer = dynamic(
  () => import('../../components/renderers/PptxRenderer').then((m) => ({ default: m.PptxRenderer })),
  { ssr: false }
);

interface FileBodyProps {
  artifactId: string;
  peekType: Exclude<ArtifactType, 'NOTE' | 'ISSUE' | 'SPEC' | 'DECISION' | 'LINK'>;
}

function ContextFallback({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
      <AlertTriangle className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm text-muted-foreground max-w-xs">{message}</p>
    </div>
  );
}

export function FileBody({ artifactId, peekType }: FileBodyProps) {
  const params = useParams<{ projectId?: string }>();
  const projectId = params?.projectId;
  const { workspace } = useWorkspace();

  if (!projectId) {
    return (
      <ContextFallback message="File previews are only available from a project page. Navigate to the project that owns this file to preview it." />
    );
  }

  return (
    <FileBodyInner
      artifactId={artifactId}
      peekType={peekType}
      workspaceId={workspace.id}
      projectId={projectId}
    />
  );
}

interface InnerProps extends FileBodyProps {
  workspaceId: string;
  projectId: string;
}

function useArtifactMetadata(workspaceId: string, projectId: string, artifactId: string) {
  return useQuery({
    queryKey: ['artifacts', workspaceId, projectId, 'list-for-peek'],
    queryFn: () => artifactsApi.list(workspaceId, projectId),
    enabled: Boolean(workspaceId && projectId && artifactId),
    staleTime: 60_000,
    select: (all) => all.find((a) => a.id === artifactId) ?? null,
  });
}

function FileBodyInner({ artifactId, workspaceId, projectId }: InnerProps) {
  const artifactQuery = useArtifactMetadata(workspaceId, projectId, artifactId);
  const signedUrlQuery = useArtifactSignedUrl(workspaceId, projectId, artifactId);

  const artifact = artifactQuery.data;
  const signedUrl = signedUrlQuery.data?.url ?? '';
  const filename = artifact?.filename ?? '';
  const mimeType = artifact?.mimeType ?? '';

  const rendererType = React.useMemo(
    () => (mimeType && filename ? resolveRenderer(mimeType, filename) : 'download'),
    [mimeType, filename]
  );

  const { content, isLoading, isExpired } = useFileContent(
    signedUrl,
    rendererType,
    Boolean(signedUrl)
  );

  if (artifactQuery.isLoading || signedUrlQuery.isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-32" />
        <div className="pt-3 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (!artifact || !signedUrl) {
    return (
      <ContextFallback message="Could not load this file. It may have been deleted or you do not have access." />
    );
  }

  if (isExpired) {
    return <ContextFallback message="Preview URL expired. Close and reopen the drawer." />;
  }

  const downloadButton = (
    <Button asChild variant="outline" size="sm">
      <a href={signedUrl} target="_blank" rel="noopener noreferrer" download={filename}>
        <Download className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
        Download
      </a>
    </Button>
  );

  const renderPreview = (): React.ReactNode => {
    if (isLoading) return <ProseSkeleton />;
    if (!content) {
      return (
        <div className="p-6 flex flex-col items-center gap-3 text-center">
          <p className="text-sm text-muted-foreground">
            This file type cannot be previewed inline.
          </p>
          {downloadButton}
        </div>
      );
    }
    switch (rendererType) {
      case 'markdown':
        return <MarkdownRenderer content={content as string} />;
      case 'text':
        return <TextRenderer content={content as string} />;
      case 'json':
        return <JsonRenderer content={content as string} />;
      case 'code':
        return (
          <CodeRenderer content={content as string} language={getLanguageForFile(filename)} />
        );
      case 'html-preview':
        return <HtmlRenderer content={content as string} filename={filename} />;
      case 'csv':
        return <CsvRenderer content={content as string} />;
      case 'image':
        return <ImageRenderer signedUrl={signedUrl} filename={filename} />;
      case 'xlsx':
        return (
          <XlsxRenderer
            content={content as ArrayBuffer}
            filename={filename}
            signedUrl={signedUrl}
          />
        );
      case 'docx':
        return (
          <DocxRenderer
            content={content as ArrayBuffer}
            filename={filename}
            signedUrl={signedUrl}
            tocOpen={false}
            onTocOpenChange={() => {}}
          />
        );
      case 'pptx':
        return (
          <PptxRenderer
            content={content as ArrayBuffer}
            currentSlide={0}
            onSlideCountKnown={() => {}}
            onNavigate={() => {}}
          />
        );
      default:
        return (
          <div className="p-6 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-muted-foreground">Preview not available for this file.</p>
            {downloadButton}
          </div>
        );
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 flex items-center justify-between gap-3 border-b border-border/60 px-5 py-2.5 bg-card/50">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{filename}</p>
          <p className="text-xs text-muted-foreground">
            {mimeType || 'unknown'} · {formatFileSize(artifact.sizeBytes)}
          </p>
        </div>
        {downloadButton}
      </div>
      <div className="flex-1 overflow-auto min-h-0">
        <React.Suspense fallback={<ProseSkeleton />}>{renderPreview()}</React.Suspense>
      </div>
    </div>
  );
}

const SIZE_UNITS = ['B', 'KB', 'MB', 'GB'] as const;

function formatFileSize(bytes: number): string {
  if (!bytes || bytes < 0) return '—';
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), SIZE_UNITS.length - 1);
  const value = bytes / Math.pow(1024, exp);
  return `${value.toFixed(value >= 10 || exp === 0 ? 0 : 1)} ${SIZE_UNITS[exp]}`;
}
