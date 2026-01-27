/**
 * Issue Extraction Panel Component.
 *
 * Main panel for extracting issues from notes with AI.
 * Features:
 * - Extract button with loading state
 * - Display extracted issues with confidence tags
 * - Issue selection and approval
 * - Real-time streaming updates
 *
 * @module features/notes/components/IssueExtractionPanel
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T154
 */

import { useState, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';
import { ExtractedIssueCard } from './ExtractedIssueCard';
import { IssueExtractionApprovalModal } from './IssueExtractionApprovalModal';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';
import { getErrorUserMessage } from '@/types/ai-errors';
import type { ExtractedIssue } from '@/stores/ai';

interface IssueExtractionPanelProps {
  noteId: string;
}

export const IssueExtractionPanel = observer(function IssueExtractionPanel({
  noteId,
}: IssueExtractionPanelProps) {
  const store = useStore();
  const { issueExtraction } = store.aiStore;
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [selectedIssues, setSelectedIssues] = useState<number[]>([]);

  const handleExtract = useCallback(() => {
    setSelectedIssues([]);
    issueExtraction.extractIssues(noteId);
  }, [noteId, issueExtraction]);

  const handleToggleIssue = useCallback((index: number) => {
    setSelectedIssues((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedIssues.length === issueExtraction.extractedIssues.length) {
      setSelectedIssues([]);
    } else {
      setSelectedIssues(issueExtraction.extractedIssues.map((_: ExtractedIssue, i: number) => i));
    }
  }, [selectedIssues.length, issueExtraction.extractedIssues]);

  const handleSelectRecommended = useCallback(() => {
    const recommendedIndices = issueExtraction.extractedIssues
      .map((issue: ExtractedIssue, i: number) => (issue.confidence_score > 0.8 ? i : -1))
      .filter((i: number) => i !== -1);
    setSelectedIssues(recommendedIndices);
  }, [issueExtraction.extractedIssues]);

  const handleCreateIssues = useCallback(() => {
    if (selectedIssues.length > 0) {
      setShowApprovalModal(true);
    }
  }, [selectedIssues.length]);

  const handleApproved = useCallback(() => {
    setSelectedIssues([]);
  }, []);

  const isEmpty = !issueExtraction.isLoading && !issueExtraction.extractedIssues.length;
  const hasIssues = issueExtraction.extractedIssues.length > 0;
  const hasRecommended = issueExtraction.hasRecommendedIssues;
  const allSelected = hasIssues && selectedIssues.length === issueExtraction.extractedIssues.length;

  return (
    <div className="issue-extraction-panel space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          Extract Issues
        </h3>
      </div>

      {isEmpty && (
        <div className="text-center py-8 px-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            Extract actionable issues from this note using AI analysis.
          </p>
          <Button onClick={handleExtract} size="lg" className="gap-2">
            <Sparkles className="h-4 w-4" />
            Extract Issues
          </Button>
        </div>
      )}

      {issueExtraction.isLoading && (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Analyzing note content...</p>
          {issueExtraction.extractedIssues.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Found {issueExtraction.extractedIssues.length} issue
              {issueExtraction.extractedIssues.length > 1 ? 's' : ''} so far
            </p>
          )}
        </div>
      )}

      {issueExtraction.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{getErrorUserMessage(issueExtraction.error)}</AlertDescription>
        </Alert>
      )}

      {hasIssues && (
        <>
          <div className="flex items-center justify-between gap-2 pb-2 border-b">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {issueExtraction.totalCount} issue{issueExtraction.totalCount > 1 ? 's' : ''} found
              </span>
              {hasRecommended && (
                <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                  {issueExtraction.recommendedCount} recommended
                </span>
              )}
            </div>
            <div className="flex gap-2">
              {hasRecommended && (
                <Button variant="ghost" size="sm" onClick={handleSelectRecommended}>
                  Select Recommended
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={handleSelectAll}>
                {allSelected ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            {issueExtraction.extractedIssues.map((issue: ExtractedIssue, index: number) => (
              <ExtractedIssueCard
                key={index}
                issue={issue}
                selected={selectedIssues.includes(index)}
                onToggle={() => handleToggleIssue(index)}
              />
            ))}
          </div>

          <div className="flex justify-between items-center pt-4 border-t">
            <span className="text-sm text-muted-foreground">
              {selectedIssues.length} of {issueExtraction.extractedIssues.length} selected
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExtract}
                disabled={issueExtraction.isLoading}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Extract Again
              </Button>
              <Button onClick={handleCreateIssues} disabled={selectedIssues.length === 0}>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Create Selected Issues
              </Button>
            </div>
          </div>
        </>
      )}

      <IssueExtractionApprovalModal
        open={showApprovalModal}
        onOpenChange={setShowApprovalModal}
        selectedIndices={selectedIssues}
        issues={issueExtraction.extractedIssues}
        onApproved={handleApproved}
      />
    </div>
  );
});
