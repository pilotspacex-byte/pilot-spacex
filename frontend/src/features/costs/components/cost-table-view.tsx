'use client';

/**
 * Cost Table View - Detailed table of cost records.
 *
 * T204: Displays sortable, filterable table of costs by user
 * with columns for user name, requests, total cost.
 *
 * @example
 * ```tsx
 * <CostTableView
 *   data={[{ user_id: '...', user_name: 'John Doe', total_cost_usd: 12.34 }]}
 * />
 * ```
 */

import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

// ============================================================================
// Types
// ============================================================================

export interface CostByUser {
  user_id: string;
  user_name: string;
  total_cost_usd: number;
  request_count: number;
}

export interface CostTableViewProps {
  /** User cost data */
  data: CostByUser[];
  /** Additional class name */
  className?: string;
}

type SortColumn = 'user_name' | 'total_cost_usd' | 'request_count' | 'avg_cost';
type SortDirection = 'asc' | 'desc';

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format cost for display.
 */
function formatCost(cost: number): string {
  if (cost < 0.01) return '<$0.01';
  return `$${cost.toFixed(2)}`;
}

/**
 * Get user initials for avatar.
 */
function getUserInitials(name: string): string {
  const parts = name.split(' ');
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Sort icon component.
 */
function SortIcon({
  column,
  sortColumn,
  sortDirection,
}: {
  column: SortColumn;
  sortColumn: SortColumn;
  sortDirection: SortDirection;
}) {
  if (sortColumn !== column) {
    return <ArrowUpDown className="ml-2 size-4 text-muted-foreground" />;
  }
  return sortDirection === 'asc' ? (
    <ArrowUp className="ml-2 size-4" />
  ) : (
    <ArrowDown className="ml-2 size-4" />
  );
}

// ============================================================================
// Component
// ============================================================================

export function CostTableView({ data, className }: CostTableViewProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('total_cost_usd');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const hasData = data && data.length > 0;

  // Handle sort toggle
  const handleSort = (column: SortColumn) => {
    if (column === sortColumn) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!hasData) return [];

    return [...data].sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      switch (sortColumn) {
        case 'user_name':
          aValue = a.user_name.toLowerCase();
          bValue = b.user_name.toLowerCase();
          break;
        case 'total_cost_usd':
          aValue = a.total_cost_usd;
          bValue = b.total_cost_usd;
          break;
        case 'request_count':
          aValue = a.request_count;
          bValue = b.request_count;
          break;
        case 'avg_cost':
          aValue = a.request_count > 0 ? a.total_cost_usd / a.request_count : 0;
          bValue = b.request_count > 0 ? b.total_cost_usd / b.request_count : 0;
          break;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
  }, [data, sortColumn, sortDirection, hasData]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Cost by User</CardTitle>
        <CardDescription>Detailed breakdown of AI usage costs per user</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            <p className="text-sm">No user cost data available for this period</p>
          </div>
        ) : (
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 lg:px-3"
                      onClick={() => handleSort('user_name')}
                    >
                      User
                      <SortIcon
                        column="user_name"
                        sortColumn={sortColumn}
                        sortDirection={sortDirection}
                      />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 lg:px-3"
                      onClick={() => handleSort('request_count')}
                    >
                      Requests
                      <SortIcon
                        column="request_count"
                        sortColumn={sortColumn}
                        sortDirection={sortDirection}
                      />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 lg:px-3"
                      onClick={() => handleSort('total_cost_usd')}
                    >
                      Total Cost
                      <SortIcon
                        column="total_cost_usd"
                        sortColumn={sortColumn}
                        sortDirection={sortDirection}
                      />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 lg:px-3"
                      onClick={() => handleSort('avg_cost')}
                    >
                      Avg/Request
                      <SortIcon
                        column="avg_cost"
                        sortColumn={sortColumn}
                        sortDirection={sortDirection}
                      />
                    </Button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((user) => {
                  const avgCost =
                    user.request_count > 0 ? user.total_cost_usd / user.request_count : 0;

                  return (
                    <TableRow key={user.user_id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="size-8">
                            <AvatarFallback className="text-xs">
                              {getUserInitials(user.user_name)}
                            </AvatarFallback>
                          </Avatar>
                          <span className="font-medium">{user.user_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {user.request_count.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-medium">
                        {formatCost(user.total_cost_usd)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-muted-foreground">
                        {formatCost(avgCost)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default CostTableView;
