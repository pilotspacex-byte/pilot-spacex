# AI UI Patterns v2.0

This document outlines UI patterns for AI features in Pilot Space, ensuring compliance with requirements FR-020 (clearly label AI content) and FR-021 (human approval for AI actions).

**Design Direction**: Warm, Capable, Collaborative

AI is positioned as a **collaborative partner** (Pilot), not a system or tool. The visual language emphasizes collaboration, trust, and shared ownership.

## Core Principles

1. **Collaborative Attribution**: AI contributions are marked as "You + AI" - emphasizing partnership
2. **Transparency**: Clear visual indicators distinguish AI-assisted content
3. **Human Control**: Users must approve AI actions that create, modify, or delete data
4. **Confidence Communication**: Show confidence levels with appropriate visual weight
5. **Friendly Voice**: AI speaks as a helpful teammate, not a cold system

## Visual Identity

### The Pilot Icon

The compass/north star icon represents the AI collaborative partner - guiding and navigating through the development process together.

```tsx
import { Compass } from 'lucide-react';
import { PilotIcon, AIAvatar } from '@/components/badge';

// Simple icon usage
<PilotIcon size="md" />

// Full avatar
<AIAvatar size="lg" />
```

### AI Color Palette

The dusty blue palette creates a calm, trustworthy presence that complements human content without competing:

| Token | Value | Usage |
|-------|-------|-------|
| `--ai` | `hsl(210 40% 55%)` | Primary AI accent |
| `--ai-foreground` | `hsl(0 0% 100%)` | Text on AI background |
| `--ai-muted` | `hsl(210 30% 94%)` | Subtle AI backgrounds |
| `--ai-border` | `hsl(210 40% 75%)` | AI container borders |

### Confidence Colors

| Level | Range | Color | Token |
|-------|-------|-------|-------|
| High | >= 80% | Teal | `--ai-confidence-high` |
| Medium | 50-79% | Warm amber | `--ai-confidence-medium` |
| Low | < 50% | Warm coral | `--ai-confidence-low` |

## Component Patterns

### AI Badge

For labeling AI-generated or AI-suggested content:

```tsx
import { AIBadge } from '@/components/badge';

// Suggestion (lightbulb icon)
<AIBadge type="suggestion">Suggested</AIBadge>

// Generated content (sparkles icon)
<AIBadge type="generated">Generated</AIBadge>

// Collaborative (compass icon)
<AIBadge type="collaborative">Pilot</AIBadge>

// With confidence
<AIBadge type="suggestion" confidence={85}>
  Suggested
</AIBadge>
```

### AI Attribution

Shows "You + AI" collaborative attribution:

```tsx
import { AIAttribution } from '@/components/badge';

// Full attribution
<AIAttribution human="You" />
// Renders: "You + [Pilot Icon] AI"

// Compact (icon only)
<AIAttribution compact />

// With custom name
<AIAttribution human="Sarah" />
// Renders: "Sarah + [Pilot Icon] AI"
```

### AI Container

Styled container for AI-generated content blocks:

```tsx
import { AICard, Card } from '@/components/card';

// Using AICard component
<AICard>
  <CardHeader>
    <div className="flex items-center gap-2">
      <PilotIcon size="sm" />
      <CardTitle>AI Suggestion</CardTitle>
    </div>
  </CardHeader>
  <CardContent>
    {content}
  </CardContent>
</AICard>

// Using CSS class
<div className="ai-container">
  {aiGeneratedContent}
</div>
```

**Styling:**
- Soft dusty blue left border (3px)
- Light blue-tinted background
- Squircle corners (rounded-2xl)
- Subtle shadow

## Suggestion Patterns

### Inline Suggestions

For text enhancement (titles, descriptions):

```tsx
<AICard variant="ai">
  <CardHeader>
    <div className="flex items-center gap-2">
      <AIBadge type="suggestion" />
      <span className="text-sm text-muted-foreground">
        Pilot suggests
      </span>
    </div>
  </CardHeader>

  <CardContent className="prose">
    {suggestion.value}
  </CardContent>

  <CardFooter className="gap-2">
    <Button variant="ai" onClick={accept}>
      Accept
    </Button>
    <Button variant="ghost" onClick={reject}>
      Dismiss
    </Button>
  </CardFooter>
</AICard>
```

### Batch Suggestions

For multiple suggestions (labels, assignees):

```tsx
<div className="space-y-2">
  {suggestions.map(suggestion => (
    <div
      key={suggestion.id}
      className="flex items-center justify-between rounded-xl border border-ai-border bg-ai-muted/30 p-3"
    >
      <div className="flex items-center gap-3">
        <span className="font-medium">{suggestion.value}</span>
        <ConfidenceIndicator confidence={suggestion.confidence} />
      </div>
      <div className="flex gap-1">
        <Button
          size="icon-sm"
          variant="ai-subtle"
          onClick={() => accept(suggestion)}
        >
          <Check className="h-4 w-4" />
        </Button>
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={() => reject(suggestion)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  ))}
</div>
```

### Accept/Reject Actions

Each suggestion must be independently actionable:

- **Accept**: Apply the suggestion immediately
- **Modify**: Edit before applying (when applicable)
- **Reject**: Dismiss without applying
- **Regenerate**: Request a new suggestion

Button styling:
- Accept uses `variant="ai"` (solid dusty blue)
- Secondary actions use `variant="ai-subtle"` (outlined)
- Reject uses `variant="ghost"`

## Loading States

### During AI Processing

```tsx
import { AILoadingSkeleton } from '@/components/skeleton';

<AILoadingSkeleton message="Analyzing content..." />

// Or custom loading
<div className="ai-container flex items-center gap-3">
  <Loader2 className="h-5 w-5 animate-spin text-ai" />
  <span className="text-sm text-ai">
    Pilot is analyzing your code...
  </span>
</div>
```

**Guidelines:**
- Use the dusty blue color for loading indicators
- Provide descriptive, friendly text about what's happening
- Show estimated time for longer operations (>5s)
- Maintain the AI container styling during loading

### Streaming Responses

For real-time AI generation:

```tsx
<AICard>
  <CardHeader>
    <div className="flex items-center gap-2">
      <AIBadge type="generated" />
      <span className="text-xs text-muted-foreground">Generating...</span>
    </div>
  </CardHeader>
  <CardContent className="prose">
    {streamedContent}
    <span className="inline-block w-0.5 h-4 bg-ai animate-pulse ml-0.5" />
  </CardContent>
</AICard>
```

## Approval Patterns (DD-003)

Per DD-003 (Critical-Only Approval), AI actions are classified by impact:

**Auto-Execute (Non-destructive)**: Suggestions, ghost text, annotations, PR comments, notifications
**Require Approval (Destructive/Critical)**: Create sub-issues, delete content, archive, publish, merge PRs

### Critical Actions (FR-021)

AI actions that create, modify, or delete data require explicit approval:

```tsx
import { AIDialog } from '@/components/dialog';

<AIDialog
  open={showApproval}
  onOpenChange={setShowApproval}
  title="Review Generated Tasks"
  description={`Pilot has generated ${tasks.length} tasks. Review and approve before creating.`}
  onApprove={handleApprove}
  onReject={handleReject}
  approveLabel="Create Tasks"
  rejectLabel="Cancel"
>
  <div className="space-y-3 max-h-80 overflow-y-auto">
    {tasks.map(task => (
      <TaskPreview
        key={task.id}
        task={task}
        onEdit={editTask}
        onRemove={removeTask}
      />
    ))}
  </div>
</AIDialog>
```

### PR Review Comments

AI review comments posted to GitHub are marked as AI-generated:

```tsx
<AICard className="space-y-3">
  <div className="flex items-center gap-2">
    <AIAvatar size="sm" />
    <span className="font-medium text-ai">Pilot</span>
    <Badge variant={severityVariant}>{severity}</Badge>
  </div>

  <p className="text-sm">{description}</p>

  {suggestedFix && (
    <div className="rounded-xl bg-muted/50 p-3">
      <p className="text-xs font-medium mb-2">Suggested Fix</p>
      <pre className="text-xs">{suggestedFix}</pre>
    </div>
  )}

  <div className="flex gap-2">
    <Button size="sm" variant="ai-subtle" onClick={resolve}>
      Mark Resolved
    </Button>
    <Button size="sm" variant="ghost" onClick={dismiss}>
      Dismiss
    </Button>
  </div>
</AICard>
```

## Error Handling

### API Key Issues

```tsx
import { AlertTriangle } from 'lucide-react';

<Alert variant="warning">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Pilot is unavailable</AlertTitle>
  <AlertDescription>
    Your API key is invalid or expired.
    <Link href="/settings/ai" className="text-primary ml-1">
      Configure API keys
    </Link>
  </AlertDescription>
</Alert>
```

### Rate Limits

```tsx
import { Clock } from 'lucide-react';

<Alert variant="info">
  <Clock className="h-4 w-4" />
  <AlertTitle>Review queued</AlertTitle>
  <AlertDescription>
    Due to API limits, your PR review has been queued.
    Pilot will complete it in ~5 minutes.
  </AlertDescription>
</Alert>
```

### Low Confidence Warning

```tsx
<Alert variant="warning" className="border-ai-confidence-low">
  <AlertTriangle className="h-4 w-4 text-ai-confidence-low" />
  <AlertTitle>Low confidence suggestion</AlertTitle>
  <AlertDescription>
    Pilot is {confidence}% confident about this suggestion.
    Please review carefully before accepting.
  </AlertDescription>
</Alert>
```

## Duplicate Detection

### Warning UI

```tsx
<Alert variant="warning">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Potential duplicates found</AlertTitle>
  <AlertDescription>
    <p className="mb-2">Pilot found similar issues:</p>
    <ul className="space-y-1">
      {duplicates.map(dup => (
        <li key={dup.id} className="flex items-center gap-2">
          <Link href={`/issues/${dup.id}`} className="text-primary">
            {dup.identifier}
          </Link>
          <span className="text-muted-foreground truncate flex-1">
            {dup.title}
          </span>
          <Badge variant="outline">
            {Math.round(dup.similarity * 100)}% match
          </Badge>
        </li>
      ))}
    </ul>
  </AlertDescription>
  <AlertActions className="mt-3">
    <Button variant="ghost" size="sm" onClick={viewDuplicates}>
      View Issues
    </Button>
    <Button variant="default" size="sm" onClick={continueAnyway}>
      Continue Anyway
    </Button>
  </AlertActions>
</Alert>
```

## Voice & Tone

AI messages should feel like a helpful teammate:

| Instead of... | Use... |
|---------------|--------|
| "AI has generated..." | "Pilot suggests..." |
| "Automated analysis complete" | "Here's what Pilot found" |
| "Error: Invalid input" | "Pilot couldn't understand that. Try..." |
| "Processing request" | "Pilot is working on it..." |
| "Suggestion rejected" | "Got it, moving on" |

## Testing Checklist

- [ ] All AI content has visual indicator (badge/container)
- [ ] Pilot icon/avatar used consistently
- [ ] "You + AI" attribution shown for collaborative content
- [ ] Confidence levels displayed when available
- [ ] Individual accept/reject for each suggestion
- [ ] Approval dialog for create/modify/delete actions
- [ ] Loading states use AI styling
- [ ] Error states are friendly and actionable
- [ ] Low confidence warnings displayed
- [ ] Duplicate detection alerts shown
- [ ] AI voice is warm and collaborative
- [ ] All AI actions can be dismissed/rejected
