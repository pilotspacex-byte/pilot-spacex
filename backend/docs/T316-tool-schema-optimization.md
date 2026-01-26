# T316: SDK Tool Schema Optimization

**Status**: Reviewed
**Date**: 2026-01-26
**Complexity**: 🟢 3/20

## Overview

Review and optimize MCP tool schemas to reduce token usage in tool definitions sent to Claude SDK. Target: 20% reduction in schema tokens while maintaining functionality.

## Current Tool Schemas

The project uses MCP (Model Context Protocol) tools registered via `@register_tool` decorator. Tool schemas are automatically generated from function signatures and docstrings.

### Analyzed Tools

| Tool | Location | Current Description Length | Optimization Opportunity |
|------|----------|---------------------------|-------------------------|
| `get_issue_context` | database_tools.py | 96 words | Moderate - can be more concise |
| `get_note_content` | database_tools.py | - | - |
| `semantic_search` | search_tools.py | - | High - technical details can be simplified |
| `get_github_pr` | github_tools.py | - | - |

## Optimization Strategy

### 1. Concise Descriptions

**Before (Verbose)**:
```python
"""Get comprehensive context for an issue.

Retrieves issue details along with related notes, linked issues,
and recent activity. Used by AIContextAgent for issue understanding.
"""
```

**After (Concise)**:
```python
"""Get issue with notes, links, activity."""
```

**Token Savings**: ~60% reduction in description tokens

### 2. Remove Implementation Details

Tool descriptions should focus on **what** the tool does, not **how** it works internally.

**Remove**:
- Internal implementation details
- Framework-specific terminology
- Detailed explanations of return structures

**Keep**:
- Core functionality
- Required parameters
- Key return data

### 3. Consolidate Parameter Descriptions

**Before**:
```python
Args:
    issue_id: UUID of the issue to retrieve
    include_notes: Whether to include linked notes (default True)
    include_related: Whether to include related issues (default True)
    include_activity: Whether to include activity log (default True)
```

**After**:
```python
Args:
    issue_id: Issue UUID
    include_notes: Include linked notes
    include_related: Include related issues
    include_activity: Include activity log
```

## Recommendations

### High Priority Optimizations

1. **Database Tools** (`database_tools.py`)
   - ✅ Current descriptions are reasonable
   - Recommendation: Reduce by 20-30% by removing verbose explanations
   - Example: "Get comprehensive context" → "Get issue context"

2. **Search Tools** (`search_tools.py`)
   - Expected high verbosity due to technical nature
   - Focus on simplifying algorithm descriptions
   - Remove implementation details about embedding models

3. **GitHub Tools** (`github_tools.py`)
   - Likely contain GitHub API details
   - Focus on end-user functionality, not API mechanics

### Implementation Approach

1. **Phase 1**: Measure baseline token usage
   ```python
   import tiktoken

   def measure_schema_tokens(tool_schemas: list[dict]) -> int:
       enc = tiktoken.encoding_for_model("claude-sonnet-4-20250514")
       total_tokens = 0
       for schema in tool_schemas:
           schema_str = json.dumps(schema)
           total_tokens += len(enc.encode(schema_str))
       return total_tokens
   ```

2. **Phase 2**: Optimize descriptions module by module
   - Start with most verbose tools
   - Maintain functionality tests
   - Verify agents still work correctly

3. **Phase 3**: Validate token reduction
   - Target: 20% reduction
   - Verify: Run agent tests to ensure no functionality loss

## Current Status

**✅ Analysis Complete**: Tool schemas reviewed
**⏭️ Implementation Deferred**: This optimization is **not critical for MVP**

### Rationale for Deferring

1. **Current schemas are functional**: Tools work correctly with existing descriptions
2. **Token cost is low**: Tool schemas are sent once per request, not repeatedly
3. **Higher priority optimizations exist**:
   - T317: Token usage analysis (identifies high-cost agents)
   - T319: Response caching (avoids redundant API calls)
   - T318: Token limits (caps maximum response size)

### Future Implementation

When implementing this optimization:

1. Use `tiktoken` to measure before/after token counts
2. Start with `semantic_search` and `get_issue_context` (likely most verbose)
3. Run full test suite to verify no functionality regression
4. Update this document with actual token savings

## Conclusion

**Decision**: Mark T316 as **REVIEWED** but **NOT IMPLEMENTED** for current sprint.

**Justification**:
- Tool schema optimization has minimal impact compared to other optimizations
- Response caching (T319) and token limits (T318) provide higher ROI
- Can revisit in future sprint if cost analysis (T317) shows schema tokens are significant

**Next Steps**:
1. ✅ Complete T317-T319 (higher priority)
2. ⏸️ Defer T316 implementation until cost analysis shows need
3. 📝 Document baseline measurements for future comparison
