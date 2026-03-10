/**
 * WorkspaceSkillCard — Admin UI for a workspace-level role skill.
 * Shows pending/active state + activate/remove actions.
 *
 * NOTE: is_active is a one-way gate. No Deactivate button — remove and regenerate to revert.
 * Source: Phase 16, WRSKL-01, WRSKL-02
 */

'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { WorkspaceRoleSkill } from '@/services/api/workspace-role-skills';

interface WorkspaceSkillCardProps {
  skill: WorkspaceRoleSkill;
  onActivate: (skillId: string) => void;
  onRemove: (skillId: string) => void;
  isActivating?: boolean;
  isRemoving?: boolean;
}

export function WorkspaceSkillCard({
  skill,
  onActivate,
  onRemove,
  isActivating = false,
  isRemoving = false,
}: WorkspaceSkillCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{skill.role_name}</span>
            {skill.is_active ? (
              <Badge variant="default" className="bg-green-500 hover:bg-green-500">
                Active
              </Badge>
            ) : (
              <Badge variant="outline" className="border-yellow-500 text-yellow-600">
                Pending Review
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{skill.role_type.replace(/_/g, ' ')}</p>
        </div>
        <div className="flex gap-2">
          {!skill.is_active && (
            <Button
              variant="default"
              size="sm"
              onClick={() => onActivate(skill.id)}
              disabled={isActivating}
            >
              Activate
            </Button>
          )}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onRemove(skill.id)}
            disabled={isRemoving}
          >
            Remove
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3 font-mono whitespace-pre-wrap">
          {skill.skill_content.slice(0, 300)}
          {skill.skill_content.length > 300 ? '\u2026' : ''}
        </p>
      </CardContent>
    </Card>
  );
}
