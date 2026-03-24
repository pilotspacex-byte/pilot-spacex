/**
 * MCPServerDialog - Modal for adding/editing MCP servers.
 *
 * Phase 25: Two tabs (Import JSON default on add, Form Configuration),
 * 720px wide, Test Connection button, Cancel + primary action footer.
 */

'use client';

import * as React from 'react';
import { Loader2, Plug } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { FormConfigTab } from './form-config-tab';
import { ImportJsonTab } from './import-json-tab';
import { McpStatusBadge } from './mcp-status-badge';
import type {
  MCPServer,
  MCPServerRegisterRequest,
  MCPServerUpdateRequest,
  MCPServerTestResult,
} from '@/stores/ai/MCPServersStore';

interface MCPServerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: MCPServer;
  onSave: (data: MCPServerRegisterRequest | MCPServerUpdateRequest) => Promise<void>;
  onImport: (jsonString: string) => Promise<void>;
  onTestConnection?: (serverId: string) => Promise<MCPServerTestResult>;
  isSaving: boolean;
}

export function MCPServerDialog({
  open,
  onOpenChange,
  initialData,
  onSave,
  onImport,
  onTestConnection,
  isSaving,
}: MCPServerDialogProps) {
  const isEdit = !!initialData;
  const defaultTab = isEdit ? 'form' : 'import';
  const formId = React.useId() + '-mcp-form';

  const [activeTab, setActiveTab] = React.useState(defaultTab);
  const [testResult, setTestResult] = React.useState<MCPServerTestResult | null>(null);
  const [isTesting, setIsTesting] = React.useState(false);

  // Reset test result and tab when dialog opens/closes
  React.useEffect(() => {
    if (!open) {
      setTestResult(null);
      setIsTesting(false);
      setActiveTab(defaultTab);
    }
  }, [open, defaultTab]);

  const handleTestConnection = async () => {
    if (!initialData || !onTestConnection) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await onTestConnection(initialData.id);
      setTestResult(result);
    } catch {
      // Error is handled by store
    } finally {
      setIsTesting(false);
    }
  };

  const handleFormSave = async (data: MCPServerRegisterRequest | MCPServerUpdateRequest) => {
    await onSave(data);
  };

  const handleImport = async (jsonString: string) => {
    await onImport(jsonString);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[720px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit MCP Server' : 'Add New MCP Server'}</DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="w-full">
            {!isEdit && <TabsTrigger value="import" className="flex-1">Import JSON</TabsTrigger>}
            <TabsTrigger value="form" className="flex-1">Form Configuration</TabsTrigger>
          </TabsList>

          {!isEdit && (
            <TabsContent value="import" forceMount className={activeTab !== 'import' ? 'hidden' : 'mt-4'}>
              <ImportJsonTab onImport={handleImport} isImporting={isSaving} />
            </TabsContent>
          )}

          <TabsContent value="form" forceMount className={activeTab !== 'form' ? 'hidden' : 'mt-4'}>
            <FormConfigTab
              initialData={initialData}
              onSave={handleFormSave}
              isSaving={isSaving}
              formId={formId}
            />

            {/* Footer for form tab */}
            <DialogFooter className="mt-6 flex items-center gap-2">
              {/* Test result inline */}
              {testResult && (
                <div className="flex items-center gap-2 mr-auto">
                  <McpStatusBadge status={testResult.status} />
                  {testResult.latency_ms != null && (
                    <span className="text-xs text-muted-foreground">{testResult.latency_ms}ms</span>
                  )}
                  {testResult.error_detail && (
                    <span className="text-xs text-destructive truncate max-w-[200px]">
                      {testResult.error_detail}
                    </span>
                  )}
                </div>
              )}

              {/* Test Connection (only in edit mode with existing server) */}
              {isEdit && onTestConnection && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  className="gap-1.5"
                >
                  {isTesting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plug className="h-4 w-4" />
                  )}
                  Test Connection
                </Button>
              )}

              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                form={formId}
                disabled={isSaving}
              >
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? 'Save Changes' : 'Save Configuration'}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
