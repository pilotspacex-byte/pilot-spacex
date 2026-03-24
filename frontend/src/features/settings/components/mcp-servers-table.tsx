/**
 * MCPServersTable - Data table with filter bar for MCP server management.
 *
 * Phase 25: Full table view with Type/Status/Search filters, server columns,
 * status badge, and row actions.
 */

'use client';

import * as React from 'react';
import { Globe, Terminal, Search } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { McpStatusBadge } from './mcp-status-badge';
import { MCPServerRowActions } from './mcp-server-row-actions';
import type { MCPServer, McpCommandRunner, McpServerType, McpStatus } from '@/stores/ai/MCPServersStore';

interface MCPServersTableProps {
  servers: MCPServer[];
  totalCount: number;
  filterType: McpServerType | 'all';
  filterStatus: McpStatus | 'all';
  filterSearch: string;
  onFilterTypeChange: (type: McpServerType | 'all') => void;
  onFilterStatusChange: (status: McpStatus | 'all') => void;
  onFilterSearchChange: (search: string) => void;
  onEdit: (server: MCPServer) => void;
  onTestConnection: (serverId: string) => Promise<unknown> | void;
  onToggleEnabled: (serverId: string, enabled: boolean) => void;
  onDelete: (serverId: string) => void;
  deletingServerId: string | null;
  testingServerId: string | null;
}

const SERVER_TYPE_ICON: Record<McpServerType, React.ReactNode> = {
  remote: <Globe className="h-4 w-4" />,
  command: <Terminal className="h-4 w-4" />,
};

const SERVER_TYPE_LABEL: Record<McpServerType, string> = {
  remote: 'Remote',
  command: 'Command',
};

function ServerTypeBadge({ type, runner }: { type: McpServerType; runner?: McpCommandRunner | null }) {
  const label = type === 'command' ? (runner ?? 'command') : SERVER_TYPE_LABEL[type];
  return (
    <Badge variant={type === 'remote' ? 'default' : 'secondary'} className="gap-1 text-xs">
      {SERVER_TYPE_ICON[type]}
      {label}
    </Badge>
  );
}

function TransportBadge({ transport }: { transport: string }) {
  return (
    <Badge variant="outline" className="text-xs font-mono">
      {transport}
    </Badge>
  );
}

export function MCPServersTable({
  servers,
  totalCount,
  filterType,
  filterStatus,
  filterSearch,
  onFilterTypeChange,
  onFilterStatusChange,
  onFilterSearchChange,
  onEdit,
  onTestConnection,
  onToggleEnabled,
  onDelete,
  deletingServerId,
  testingServerId,
}: MCPServersTableProps) {
  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={filterType} onValueChange={(v) => onFilterTypeChange(v as McpServerType | 'all')}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="remote">Remote</SelectItem>
            <SelectItem value="command">Command</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterStatus} onValueChange={(v) => onFilterStatusChange(v as McpStatus | 'all')}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="enabled">Enabled</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
            <SelectItem value="unhealthy">Unhealthy</SelectItem>
            <SelectItem value="unreachable">Unreachable</SelectItem>
            <SelectItem value="config_error">Config Error</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label="Search servers"
            placeholder="Search servers..."
            value={filterSearch}
            onChange={(e) => onFilterSearchChange(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[250px]">Server Name</TableHead>
              <TableHead className="w-[100px]">Type</TableHead>
              <TableHead>URL / Command</TableHead>
              <TableHead className="w-[100px]">Transport</TableHead>
              <TableHead className="w-[130px]">Status</TableHead>
              <TableHead className="w-[60px]">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {servers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No servers match the current filters.
                </TableCell>
              </TableRow>
            ) : (
              servers.map((server) => (
                <TableRow key={server.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">{SERVER_TYPE_ICON[server.server_type]}</span>
                      <span className="font-mono text-sm font-medium truncate max-w-[200px]">
                        {server.display_name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <ServerTypeBadge type={server.server_type} runner={server.command_runner} />
                  </TableCell>
                  <TableCell className="max-w-[300px]">
                    <span
                      className="text-sm text-muted-foreground font-mono block truncate"
                      title={
                        server.server_type !== 'remote' && server.command_args
                          ? `${server.url_or_command || server.url} ${server.command_args}`
                          : (server.url_or_command || server.url) ?? undefined
                      }
                    >
                      {server.server_type !== 'remote' && server.command_args
                        ? `${server.url_or_command || server.url} ${server.command_args}`
                        : (server.url_or_command || server.url)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <TransportBadge transport={server.transport} />
                  </TableCell>
                  <TableCell>
                    <McpStatusBadge status={server.last_status} />
                  </TableCell>
                  <TableCell>
                    <MCPServerRowActions
                      server={server}
                      onEdit={onEdit}
                      onTestConnection={onTestConnection}
                      onToggleEnabled={onToggleEnabled}
                      onDelete={onDelete}
                      isDeleting={deletingServerId === server.id}
                      isTesting={testingServerId === server.id}
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Footer count */}
      <div className="text-xs text-muted-foreground">
        Showing {servers.length} of {totalCount} servers
      </div>
    </div>
  );
}
