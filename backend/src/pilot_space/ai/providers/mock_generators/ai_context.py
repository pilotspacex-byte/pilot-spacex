"""Mock AI context generator.

Provides deterministic AI context generation with
summaries, tasks, and Claude Code prompts.
"""

from pilot_space.ai.agents.ai_context_agent import (
    AIContextInput,
    AIContextOutput,
)
from pilot_space.ai.providers.mock import MockResponseRegistry


@MockResponseRegistry.register("AIContextAgent")
def generate_ai_context(input_data: AIContextInput) -> AIContextOutput:
    """Generate mock AI context.

    Creates comprehensive context including:
    1. Summary and analysis
    2. Key considerations and approach
    3. Task checklist
    4. Claude Code prompt

    Args:
        input_data: AI context input.

    Returns:
        AIContextOutput with generated context.
    """
    # Generate summary
    summary = f"This issue addresses {input_data.issue_title.lower()}. "
    if input_data.issue_description:
        summary += "Based on the description, this involves implementation work "
        summary += "that requires careful attention to existing patterns."
    else:
        summary += "Further details needed to fully understand the scope."

    # Generate analysis
    analysis = f"""## Overview
This issue ({input_data.issue_identifier}) focuses on {input_data.issue_title.lower()}.

## Context
Related issues: {len(input_data.related_issues)} found
Related notes: {len(input_data.related_notes)} found
Related pages: {len(input_data.related_pages)} found
Code references: {len(input_data.code_references)} identified

## Approach
1. Review existing implementation patterns
2. Ensure consistency with codebase conventions
3. Add appropriate tests
4. Update documentation if needed
"""

    # Key considerations
    key_considerations = [
        "Maintain backward compatibility with existing functionality",
        "Follow established code patterns and conventions",
        "Ensure comprehensive test coverage",
        "Update documentation to reflect changes",
    ]

    # Suggested approach
    suggested_approach = """1. **Planning Phase**
   - Review related issues and notes
   - Identify affected components
   - Plan implementation strategy

2. **Implementation Phase**
   - Make incremental changes
   - Add unit tests
   - Verify integration points

3. **Validation Phase**
   - Run full test suite
   - Manual testing
   - Code review
"""

    # Potential blockers
    potential_blockers = [
        "May need clarification on edge cases",
        "Potential dependency on other features",
    ]

    # Generate task checklist
    tasks_checklist = [
        {
            "id": "task-1",
            "description": "Understand requirements and acceptance criteria",
            "completed": False,
            "dependencies": [],
            "estimated_effort": "S",
            "order": 1,
        },
        {
            "id": "task-2",
            "description": "Review related code and documentation",
            "completed": False,
            "dependencies": ["task-1"],
            "estimated_effort": "M",
            "order": 2,
        },
        {
            "id": "task-3",
            "description": "Implement core functionality",
            "completed": False,
            "dependencies": ["task-2"],
            "estimated_effort": "L",
            "order": 3,
        },
        {
            "id": "task-4",
            "description": "Add comprehensive tests",
            "completed": False,
            "dependencies": ["task-3"],
            "estimated_effort": "M",
            "order": 4,
        },
        {
            "id": "task-5",
            "description": "Update documentation",
            "completed": False,
            "dependencies": ["task-3"],
            "estimated_effort": "S",
            "order": 5,
        },
    ]

    # Generate Claude Code prompt
    claude_code_prompt = f"""# {input_data.issue_identifier}: {input_data.issue_title}

## Summary
{summary}

## Implementation Tasks
"""
    for task in tasks_checklist:
        claude_code_prompt += f"- [ ] {task['description']}\n"

    claude_code_prompt += """
## Code References
"""
    if input_data.code_references:
        for ref in input_data.code_references:
            claude_code_prompt += f"- {ref.file_path}"
            if ref.line_range:
                claude_code_prompt += f" (lines {ref.line_range[0]}-{ref.line_range[1]})"
            claude_code_prompt += "\n"
    else:
        claude_code_prompt += "No specific code references identified.\n"

    claude_code_prompt += f"""
## Technical Notes
{suggested_approach}

## Important Considerations
"""
    for consideration in key_considerations:
        claude_code_prompt += f"- {consideration}\n"

    # Determine complexity and effort
    complexity = "medium"
    if len(tasks_checklist) > 5:
        complexity = "high"
        estimated_effort = "L"
    elif len(tasks_checklist) <= 3:
        complexity = "low"
        estimated_effort = "S"
    else:
        estimated_effort = "M"

    return AIContextOutput(
        summary=summary,
        analysis=analysis,
        complexity=complexity,
        estimated_effort=estimated_effort,
        key_considerations=key_considerations,
        suggested_approach=suggested_approach,
        potential_blockers=potential_blockers,
        related_issues=[item.to_dict() for item in input_data.related_issues],
        related_notes=[item.to_dict() for item in input_data.related_notes],
        related_pages=[item.to_dict() for item in input_data.related_pages],
        code_references=[ref.to_dict() for ref in input_data.code_references],
        tasks_checklist=tasks_checklist,
        claude_code_prompt=claude_code_prompt,
        conversation_history=[],
        version=1,
    )


__all__ = ["generate_ai_context"]
