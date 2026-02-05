# Design Mood & Visual Direction — 008: Thinking & Tool Call UX

**Status**: Design Reference
**Date**: 2026-02-04

---

## Design Direction: "Quiet Intelligence"

The visual language for thinking and tool call states should feel like watching a skilled craftsperson work — you see the process, understand the intent, but the UI never demands attention. It whispers rather than shouts.

### Aesthetic Principles

1. **Layered Transparency** — Frosted glass surfaces create depth without heaviness. Thinking blocks feel like they float above the conversation on a translucent layer.

2. **AI as Warm Collaborator** — The dusty blue (`--ai: #6B8FAD`) is the agent's color. Every agent-activity indicator uses this color family. It's calm, trustworthy, never alarming.

3. **Progressive Disclosure** — Collapsed by default, rich on demand. Headers tell the story; details reward the curious.

4. **Temporal Awareness** — Elapsed time counters use tabular-nums and monospace for a "digital clock" precision feel. Duration badges are the primary information scent.

5. **Status Through Color, Not Words** — Running = pulsing AI blue. Complete = solid primary green. Failed = muted red. The eye learns the pattern instantly.

### Color Palette for Agent States

```
Thinking (active):   --ai (#6B8FAD) with pulse animation
Thinking (done):     --ai at 60% opacity, static
Tool running:        --ai (#6B8FAD) with subtle glow
Tool complete:       --primary (#29A386) solid
Tool failed:         --destructive (#D9534F) at 80%
Banner background:   glass-subtle (backdrop-blur-12 + 85% opacity)
Token budget green:  --primary (#29A386)
Token budget yellow: --warning (#D9853F)
Token budget red:    --destructive (#D9534F)
```

### Typography for Agent UI

```
Tool names:      font-sans, text-sm, font-medium (human-readable mapped names)
Duration badges: font-mono, text-xs, tabular-nums (precise timing)
Thinking text:   font-mono, text-[13px], leading-relaxed (raw reasoning)
Status labels:   font-sans, text-xs, font-medium, uppercase tracking-wide
```

### Motion Language

```
Thinking pulse:  2s ease-in-out infinite (existing animate-ai-pulse)
Status change:   200ms ease-out (fast, decisive)
Collapse/expand: 200ms cubic-bezier(0, 0, 0.2, 1) (existing --ease-out)
Banner phase:    150ms crossfade (one phase fades as next appears)
Reduced motion:  All animations → static opacity indicators
```

### Surface Treatment

**Thinking Block** — Frosted glass card:
- `backdrop-filter: blur(12px) saturate(150%)`
- Background: `var(--ai-muted)` (light: `#eef3f7`, dark: `#1f2d38`)
- Left border: `4px solid var(--ai)`
- Border radius: `var(--radius-md)` (10px squircle)
- During streaming: left border pulses between 30% and 100% opacity

**Tool Card** — Elevated surface:
- Background: `var(--background-subtle)`
- Border: `1px solid var(--border-subtle)`
- Border radius: `var(--radius-md)` (10px)
- Shadow: `shadow-warm-sm` on hover

**Streaming Banner** — Subtle glass strip:
- Height: 36px
- `glass-subtle` class (blur-12 + 85% background)
- Border-top: `1px solid var(--border-subtle)`
- No shadow — should feel like a natural extension of the input area

---

## Component Visual Specs

### 1. ThinkingBlock (Enhanced)

```
┌─────────────────────────────────────────────────────────┐
│ 🧠  Thinking...                              ⏱ 3.2s  ▾ │  ← Header (always visible)
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│  ← 4px AI accent left border
│                                                         │
│  Analyzing the code structure of the note module...     │  ← Monospace, streaming cursor
│  The ContentConverter needs to handle block IDs█        │
│                                                         │
└─────────────────────────────────────────────────────────┘

Collapsed (completed):
┌─────────────────────────────────────────────────────────┐
│ 🧠  Thought for 3.2s              ~120 tokens        ▸ │
└─────────────────────────────────────────────────────────┘
```

**Visual Details**:
- Frosted glass: `glass-subtle` + `bg-ai-muted`
- Left border: `border-l-[4px] border-l-ai` (pulsing during stream via `animate-ai-pulse`)
- Header: Brain icon (`lucide/Brain`), label, timer, chevron
- Timer: `font-mono text-xs tabular-nums text-ai`
- Token badge: `text-xs text-muted-foreground` — only on completed blocks
- Content area: `max-h-[400px] overflow-y-auto scrollbar-thin`
- Streaming cursor: `h-4 w-[2px] bg-ai animate-pulse`

### 2. ToolCallCard (Redesigned)

```
Running:
┌─────────────────────────────────────────────────────────┐
│  ◉  Updating Note Block                    ⏱ 1.4s   ▾ │
│     Running...                                          │
└─────────────────────────────────────────────────────────┘

Completed:
┌─────────────────────────────────────────────────────────┐
│  ✓  Updating Note Block                      0.8s    ▾ │
└─────────────────────────────────────────────────────────┘

Failed:
┌─────────────────────────────────────────────────────────┐
│  ✕  Updating Note Block                      2.1s    ▾ │
│     Permission denied: workspace_id mismatch            │
└─────────────────────────────────────────────────────────┘

Expanded (any state):
┌─────────────────────────────────────────────────────────┐
│  ✓  Updating Note Block                      0.8s    ▴ │
├─────────────────────────────────────────────────────────┤
│  Input                                                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │ {                                                 │  │
│  │   "note_id": "abc-123",                           │  │
│  │   "block_id": "blk-456",                          │  │
│  │   "content": "Updated text..."                    │  │
│  │ }                                                 │  │
│  └───────────────────────────────────────────────────┘  │
│  Output                                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │ { "status": "pending_apply" }                     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Status Icon Mapping**:
- Pending: `Circle` (muted) — hollow circle
- Running: `Loader2` (AI blue) — spinning animation
- Completed: `CheckCircle2` (primary green) — filled check
- Failed: `XCircle` (destructive red) — filled X

**Tool Name Mapping** (frontend constant):
```
update_note_block    → "Updating Note Block"
enhance_text         → "Enhancing Text"
summarize_note       → "Summarizing Note"
extract_issues       → "Extracting Issues"
create_issue_from_note → "Creating Issue"
link_existing_issues → "Linking Issues"
```

### 3. Parallel Tool Group

```
┌─ Parallel (3 tools) ────────────────────────────────────┐
│ │  ✓  Extracting Issues                       1.2s   ▾ │
│ │  ◉  Creating Issue                         ⏱ 0.6s  ▾ │
│ │  ○  Linking Issues                                  ▾ │
└─────────────────────────────────────────────────────────┘
```

**Visual**: Left border `2px solid var(--ai-border)` on the group container. Header shows "Parallel (N tools)" with `GitBranch` icon.

### 4. StreamingStateBanner

```
Fixed above input, 36px height:

Thinking phase:
┌─────────────────────────────────────────────────────────┐
│  🧠  Thinking...                                  2.1s │
└─────────────────────────────────────────────────────────┘

Tool phase:
┌─────────────────────────────────────────────────────────┐
│  ⚙  Using Extracting Issues                      0.4s │
└─────────────────────────────────────────────────────────┘

Writing phase:
┌─────────────────────────────────────────────────────────┐
│  ✎  Writing response...                          124w │
└─────────────────────────────────────────────────────────┘

Stopped:
┌─────────────────────────────────────────────────────────┐
│  ■  Stopped                                            │
└─────────────────────────────────────────────────────────┘
```

**Visual**:
- Background: `glass-subtle` treatment
- Border-top: `1px solid var(--border-subtle)`
- Icon + label: `text-sm text-muted-foreground`
- Timer/count: `font-mono text-xs tabular-nums text-ai` aligned right
- Phase transitions: `AnimatePresence` with 150ms crossfade
- Height: 36px, `flex items-center px-3`

### 5. Vertical Step Timeline

```
For messages with 3+ tool calls, toggled via "View steps" link:

  ①──── Summarizing Note ──────── 0.8s ✓
  │
  ②──── Extracting Issues ─────── 1.2s ✓
  │
  ③──── Creating Issue ──────────  ⏱ ◉
  │
  ④──── Linking Issues ────────── ○

Legend: ✓ = completed (green), ◉ = running (blue pulse), ○ = pending (muted)
```

**Visual**:
- Vertical connecting line: `2px solid var(--border-subtle)`
- Step circles: 20px diameter, centered on the line
  - Pending: `border-2 border-muted-foreground` hollow
  - Running: `bg-ai border-2 border-ai` with pulse
  - Complete: `bg-primary` with white checkmark
  - Failed: `bg-destructive` with white X
- Tool name: `text-sm font-medium`
- Duration: `font-mono text-xs tabular-nums`

### 6. Token Budget Ring

```
Near send button, 24px circular ring:

  ╭─╮
  │●│  42%     ← Green ring, tooltip shows "3.4K / 8K tokens"
  ╰─╯

At 80%:
  ╭─╮
  │●│  82%     ← Orange ring, toast notification
  ╰─╯

At 95%:
  ╭─╮
  │●│  96%     ← Red ring, pulsing
  ╰─╯
```

**Visual**:
- SVG circle with `stroke-dasharray` for progress
- 24px viewBox, 2px stroke width
- Colors: green (<60%), yellow (60-79%), orange (80-94%), red (95%+)
- Tooltip (shadcn `Tooltip`): "3.4K / 8K tokens (42%)"
- Positioned in ChatInput toolbar area, left of skill/agent buttons

---

## Dark Mode Adaptations

All components automatically adapt via CSS variables:
- `--ai-muted`: `#eef3f7` → `#1f2d38` (thinking block bg)
- `--ai`: `#6b8fad` → `#7da3c1` (accent color)
- `--background-subtle`: `#f8f7f5` → `#232220` (tool card bg)
- `--border-subtle`: `#f0eeeb` → `#333230` (borders)
- Frosted glass: opacity adjustments via `.dark` variant

## Reduced Motion

Per existing `globals.css` `@media (prefers-reduced-motion: reduce)`:
- All `animate-*` classes → `animation: none`
- Thinking pulse → static `opacity: 0.8` border
- Loader2 spin → static icon with `opacity: 0.6`
- Phase transitions → instant swap (no crossfade)
- Token ring pulse → static red color
