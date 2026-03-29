/**
 * Category grid for marketplace browse page.
 * 6 categories with icons, clickable to filter listings.
 * Source: Phase 055, P55-02
 */

'use client';

import {
  BarChart3,
  BookOpen,
  Code,
  FileText,
  Palette,
  Shield,
  type LucideIcon,
} from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';

// ---------------------------------------------------------------------------
// Category Data
// ---------------------------------------------------------------------------

interface Category {
  name: string;
  icon: LucideIcon;
  color: string;
}

const CATEGORIES: Category[] = [
  { name: 'Development', icon: Code, color: 'text-blue-500' },
  { name: 'Writing', icon: FileText, color: 'text-emerald-500' },
  { name: 'Analysis', icon: BarChart3, color: 'text-violet-500' },
  { name: 'Documentation', icon: BookOpen, color: 'text-amber-500' },
  { name: 'Security', icon: Shield, color: 'text-red-500' },
  { name: 'Design', icon: Palette, color: 'text-pink-500' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CategoryGridProps {
  onCategorySelect: (category: string) => void;
}

export function CategoryGrid({ onCategorySelect }: CategoryGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {CATEGORIES.map((cat) => {
        const Icon = cat.icon;
        return (
          <Card
            key={cat.name}
            className="cursor-pointer transition-shadow hover:shadow-md"
            onClick={() => onCategorySelect(cat.name)}
          >
            <CardContent className="flex items-center gap-3 py-4">
              <div className={`${cat.color}`}>
                <Icon className="h-6 w-6" />
              </div>
              <span className="text-sm font-medium">{cat.name}</span>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
