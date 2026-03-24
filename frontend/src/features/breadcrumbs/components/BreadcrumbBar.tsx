'use client';

import { observer } from 'mobx-react-lite';
import { useFileStore } from '@/stores/RootStore';
import type { FileTreeItem } from '@/features/file-browser/hooks/useFileTree';
import { useBreadcrumbs } from '../hooks/useBreadcrumbs';
import { BreadcrumbSegment } from './BreadcrumbSegment';

interface BreadcrumbBarProps {
  fileTreeItems: FileTreeItem[];
}

/**
 * Horizontal breadcrumb bar showing the active file's path with clickable
 * segments. Each segment opens a Popover dropdown of sibling files/folders
 * for lateral navigation.
 */
export const BreadcrumbBar = observer(function BreadcrumbBar({
  fileTreeItems,
}: BreadcrumbBarProps) {
  const fileStore = useFileStore();
  const segments = useBreadcrumbs(fileStore.activeFile, fileTreeItems);

  if (segments.length === 0) return null;

  return (
    <div className="flex h-8 items-center gap-0.5 overflow-x-auto border-b border-border-subtle bg-background-subtle px-3">
      {segments.map((segment) => (
        <BreadcrumbSegment
          key={segment.path}
          segment={segment}
          onNavigate={(sibling) => {
            fileStore.openFile({
              id: sibling.id,
              name: sibling.name,
              path: sibling.path,
              source: fileStore.activeFile?.source ?? 'local',
              language: '',
              content: '',
              isReadOnly: false,
            });
          }}
        />
      ))}
    </div>
  );
});
