/**
 * ImportJsonTab - JSON import editor with real-time parsing and server preview.
 *
 * Phase 25: Monospace textarea, file upload, detected server cards, validation
 * summary, and Import button.
 */

'use client';

import * as React from 'react';
import { Upload, CheckCircle2, AlertCircle, Globe, Terminal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// ── Types ───────────────────────────────────────────────────

interface DetectedServer {
  name: string;
  url_or_command: string;
  transport: string;
  type: 'remote' | 'command';
  command_runner?: 'npx' | 'uvx';
}

interface ImportJsonTabProps {
  onImport: (jsonString: string) => void;
  isImporting: boolean;
}

// ── JSON Parser (client-side preview only) ─────────────────

function parseConfigJson(raw: string): DetectedServer[] {
  const parsed = JSON.parse(raw);
  const mcpServers = parsed?.mcpServers ?? parsed?.['mcp-servers'] ?? parsed;

  if (typeof mcpServers !== 'object' || mcpServers === null || Array.isArray(mcpServers)) {
    return [];
  }

  const results: DetectedServer[] = [];
  for (const [name, cfg] of Object.entries(mcpServers)) {
    if (typeof cfg !== 'object' || cfg === null) continue;
    const config = cfg as Record<string, unknown>;

    let type: DetectedServer['type'] = 'remote';
    let command_runner: DetectedServer['command_runner'];
    let urlOrCommand = '';
    let transport = 'sse';

    if (typeof config.command === 'string') {
      const cmd = config.command as string;
      const parts = cmd.split(/\s+/);
      const runner = parts[0]?.toLowerCase();
      if (runner === 'npx') command_runner = 'npx';
      else if (runner === 'uvx') command_runner = 'uvx';
      type = 'command';
      urlOrCommand = cmd;
      transport = 'stdio';
    } else if (typeof config.url === 'string') {
      urlOrCommand = config.url as string;
      type = 'remote';
      transport = (config.transport as string) || 'sse';
    } else if (typeof config.httpUrl === 'string') {
      urlOrCommand = config.httpUrl as string;
      type = 'remote';
      transport = 'streamable_http';
    }

    results.push({ name, url_or_command: urlOrCommand, transport, type, command_runner });
  }
  return results;
}

const PLACEHOLDER = `{
  "mcpServers": {
    "my-server": {
      "url": "https://mcp.example.com/sse",
      "headers": {
        "Authorization": "Bearer sk-..."
      }
    }
  }
}`;

const TYPE_ICON: Record<string, React.ReactNode> = {
  remote: <Globe className="h-4 w-4" />,
  command: <Terminal className="h-4 w-4" />,
};

// ── Component ───────────────────────────────────────────────

export function ImportJsonTab({ onImport, isImporting }: ImportJsonTabProps) {
  const [jsonText, setJsonText] = React.useState('');
  const [parseError, setParseError] = React.useState<string | null>(null);
  const [detectedServers, setDetectedServers] = React.useState<DetectedServer[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Real-time parse
  React.useEffect(() => {
    if (!jsonText.trim()) {
      setParseError(null);
      setDetectedServers([]);
      return;
    }

    try {
      const servers = parseConfigJson(jsonText);
      setDetectedServers(servers);
      setParseError(null);
    } catch (err) {
      setDetectedServers([]);
      setParseError(err instanceof SyntaxError ? err.message : 'Invalid JSON');
    }
  }, [jsonText]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result;
      if (typeof text === 'string') setJsonText(text);
    };
    reader.readAsText(file);
    // Reset so same file can be re-uploaded
    e.target.value = '';
  };

  const canImport = !parseError && detectedServers.length > 0 && !isImporting;

  return (
    <div className="space-y-4">
      {/* Info line */}
      <p className="text-xs text-muted-foreground">
        Supports Claude, Cursor, and VS Code MCP config formats.
      </p>

      {/* Textarea */}
      <div className="space-y-1.5">
        <label htmlFor="import-json-input" className="text-sm font-medium leading-none">
          Import configuration JSON
        </label>
        <textarea
          id="import-json-input"
          className="w-full h-48 rounded-md border border-border bg-muted/30 p-3 font-mono text-xs resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder={PLACEHOLDER}
          disabled={isImporting}
          spellCheck={false}
        />
      </div>

      {/* Upload file */}
      <div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={isImporting}
          className="gap-1.5"
        >
          <Upload className="h-3.5 w-3.5" />
          Upload File
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>

      {/* Validation summary */}
      {jsonText.trim() && (
        <div className="flex items-center gap-2 text-sm">
          {parseError ? (
            <>
              <AlertCircle className="h-4 w-4 text-destructive" />
              <span className="text-destructive">{parseError}</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-green-700 dark:text-green-400">
                Valid JSON — {detectedServers.length} server{detectedServers.length !== 1 ? 's' : ''}{' '}
                detected
              </span>
            </>
          )}
        </div>
      )}

      {/* Detected servers preview */}
      {detectedServers.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Detected Servers
          </p>
          <div className="space-y-2">
            {detectedServers.map((server) => (
              <div
                key={server.name}
                className="flex items-center gap-3 rounded-md border border-border p-3"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
                  {TYPE_ICON[server.type]}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium font-mono truncate">{server.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{server.url_or_command}</p>
                </div>
                <Badge variant="outline" className="text-xs font-mono shrink-0">
                  {server.transport}
                </Badge>
                {server.command_runner && (
                  <Badge variant="secondary" className="text-xs font-mono shrink-0">
                    {server.command_runner}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Import button */}
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={() => onImport(jsonText)}
          disabled={!canImport}
        >
          Import & Add Servers
        </Button>
      </div>
    </div>
  );
}
