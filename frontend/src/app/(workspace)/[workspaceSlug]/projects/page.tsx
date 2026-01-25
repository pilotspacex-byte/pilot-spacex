'use client';

import { motion } from 'motion/react';
import { FolderKanban, Plus, LayoutGrid, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const mockProjects = [
  {
    id: '1',
    name: 'Authentication',
    description: 'User auth and authorization system',
    issueCount: 12,
    completedCount: 8,
    color: 'bg-primary',
  },
  {
    id: '2',
    name: 'API Gateway',
    description: 'REST API and GraphQL endpoints',
    issueCount: 25,
    completedCount: 15,
    color: 'bg-ai',
  },
  {
    id: '3',
    name: 'Frontend',
    description: 'React frontend application',
    issueCount: 18,
    completedCount: 10,
    color: 'bg-amber-500',
  },
];

export default function ProjectsPage() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground">Organize your work into projects</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border p-1">
            <Button variant="ghost" size="icon-sm" className="h-7 w-7">
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon-sm" className="h-7 w-7">
              <List className="h-4 w-4" />
            </Button>
          </div>
          <Button className="gap-2 shadow-warm-sm">
            <Plus className="h-4 w-4" />
            New Project
          </Button>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="flex-1 overflow-auto p-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mockProjects.map((project, index) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                className={cn(
                  'group cursor-pointer transition-all duration-200',
                  'hover:shadow-warm-md hover:-translate-y-0.5'
                )}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-lg',
                        project.color + '/10'
                      )}
                    >
                      <FolderKanban
                        className={cn('h-5 w-5', project.color.replace('bg-', 'text-'))}
                      />
                    </div>
                    <div>
                      <CardTitle className="text-base transition-colors group-hover:text-primary">
                        {project.name}
                      </CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="mb-4 text-sm text-muted-foreground">{project.description}</p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {project.completedCount}/{project.issueCount} issues
                    </span>
                    <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn('h-full rounded-full', project.color)}
                        style={{
                          width: `${(project.completedCount / project.issueCount) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
