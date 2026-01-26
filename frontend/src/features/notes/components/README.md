# Note Components - Issue Extraction

This directory contains the Issue Extraction UI components for extracting actionable issues from notes using AI.

## Components

### IssueExtractionPanel

Main panel component for issue extraction. Displays extracted issues with confidence tags and handles the approval flow.

**Usage:**
```tsx
import { IssueExtractionPanel } from '@/features/notes/components/IssueExtractionPanel';

// In your note page/layout
<IssueExtractionPanel noteId={noteId} />
```

### ExtractedIssueCard

Displays a single extracted issue with confidence tag, description, labels, and selection checkbox.

### IssueExtractionApprovalModal

Modal dialog for confirming the creation of selected issues. Implements DD-003 critical approval pattern.

### Integration Example

To integrate the Issue Extraction Panel into a note page:

```tsx
// app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx
'use client';

import { observer } from 'mobx-react-lite';
import { EditorToolbar } from '@/features/notes/components/EditorToolbar';
import { IssueExtractionPanel } from '@/features/notes/components/IssueExtractionPanel';
import { Button } from '@/components/ui/button';
import { FileOutput } from 'lucide-react';
import { useState } from 'react';

export const NotePage = observer(function NotePage({ params }: { params: { noteId: string } }) {
  const [showIssuePanel, setShowIssuePanel] = useState(false);

  return (
    <div className="flex h-screen">
      {/* Main editor area */}
      <div className="flex-1 flex flex-col">
        <EditorToolbar
          noteId={params.noteId}
          // Add extract issues button
          actionSlot={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowIssuePanel(!showIssuePanel)}
            >
              <FileOutput className="h-4 w-4 mr-2" />
              Extract Issues
            </Button>
          }
        />

        {/* Note editor */}
        <div className="flex-1 overflow-auto p-6">
          {/* Your TipTap editor here */}
        </div>
      </div>

      {/* Issue extraction sidebar */}
      {showIssuePanel && (
        <div className="w-96 border-l bg-background overflow-y-auto">
          <IssueExtractionPanel noteId={params.noteId} />
        </div>
      )}
    </div>
  );
});
```

## Features

- **Streaming Extraction**: Real-time SSE streaming of extracted issues as they're analyzed
- **Confidence Tags (DD-048)**:
  - **Recommended** (green): confidence > 0.8
  - **Default** (blue): 0.6-0.8
  - **Current** (gray): matches existing patterns
  - **Alternative** (yellow): < 0.6
- **Bulk Selection**: Select all, select recommended, or individual selection
- **Approval Flow (DD-003)**: Critical approval required before creating issues
- **MobX Integration**: Reactive state management with observer pattern

## Store

The `IssueExtractionStore` (in `/stores/ai/`) manages:
- SSE streaming connection
- Extracted issues collection
- Selection state
- Approval flow
- Error handling

Access via:
```tsx
const { aiStore } = useStores();
const { issueExtraction } = aiStore;
```

## API Endpoints

- **SSE Stream**: `POST /api/v1/ai/notes/:noteId/extract-issues`
- **Approval**: `POST /ai/approvals/:approvalId/resolve`

See `backend/src/pilot_space/ai/agents/issue_extractor_sdk_agent.py` for backend implementation.
