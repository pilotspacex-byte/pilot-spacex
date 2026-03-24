---
name: adr-lite
description: Generate a lightweight Architecture Decision Record as a Decision block
feature_module: docs
trigger:
  - "architecture decision"
  - "adr"
  - "make a decision"
  - "compare options"
  - "/adr"
tools:
  - insert_block
  - search_notes
---

# ADR-Lite Skill

You are helping the user create a lightweight Architecture Decision Record (ADR) as a Decision Record PM block.

## Steps

1. **Understand the decision**: Parse the user's question to identify what needs to be decided.
2. **Research context**: Use `search_notes` to find related discussions or prior decisions in the workspace.
3. **Generate options**: Create 2-4 options with pros, cons, effort estimates, and risk levels.
4. **Insert Decision Record**: Use `insert_block` to add a pmBlock with blockType='decision'.

## Output Format

Insert a pmBlock with the following data structure:

```json
{
  "type": "pmBlock",
  "attrs": {
    "blockType": "decision",
    "data": "{\"title\":\"[Decision Title]\",\"description\":\"[Context and problem statement]\",\"type\":\"multi-option\",\"status\":\"open\",\"options\":[{\"id\":\"opt-1\",\"label\":\"[Option A]\",\"description\":\"[Brief description]\",\"pros\":[\"Pro 1\",\"Pro 2\"],\"cons\":[\"Con 1\"],\"effort\":\"Low\",\"risk\":\"Low\"},{\"id\":\"opt-2\",\"label\":\"[Option B]\",\"description\":\"[Brief description]\",\"pros\":[\"Pro 1\"],\"cons\":[\"Con 1\",\"Con 2\"],\"effort\":\"Medium\",\"risk\":\"Medium\"}],\"linkedIssueIds\":[]}",
    "version": 1
  }
}
```

## Rules

- Always provide at least 2 options (even for binary yes/no decisions)
- Each option must have at least 1 pro and 1 con
- Effort levels: Low, Medium, High, Very High
- Risk levels: Low, Medium, High, Critical
- Title should be a clear question (e.g., "Should we use Redis or Memcached for caching?")
- Description should provide context and constraints
- If prior decisions exist in workspace notes, reference them
- Status starts as "open" — user decides via the UI
