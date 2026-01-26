"""Mock commit linker generator.

Provides deterministic issue link extraction from
commit messages and PR descriptions.
"""

import re

from pilot_space.ai.agents import (
    CommitLinkerInput,
    CommitLinkerOutput,
    IssueLink,
)
from pilot_space.ai.providers.mock import MockResponseRegistry

# Issue reference pattern (e.g., PILOT-123, ABC-456)
ISSUE_REF_PATTERN = re.compile(r"([A-Z]{2,10})-(\d+)", re.IGNORECASE)

# Fix/close keywords
FIX_KEYWORDS = (
    "fix",
    "fixes",
    "fixed",
    "close",
    "closes",
    "closed",
    "resolve",
    "resolves",
    "resolved",
)


@MockResponseRegistry.register("CommitLinkerAgent")
def generate_commit_linker(input_data: CommitLinkerInput) -> CommitLinkerOutput:
    """Generate mock commit linker results.

    Extracts issue references from text:
    1. Pattern matching for PROJECT-NUMBER format
    2. Detecting fix/close keywords
    3. Filtering by project prefixes

    Args:
        input_data: Commit linker input.

    Returns:
        CommitLinkerOutput with extracted links.
    """
    text = input_data.text
    if not text:
        return CommitLinkerOutput(links=[], method="regex")

    links: list[IssueLink] = []
    seen: set[str] = set()

    # Find all issue references
    for match in ISSUE_REF_PATTERN.finditer(text):
        project = match.group(1).upper()
        number = int(match.group(2))
        identifier = f"{project}-{number}"

        # Skip duplicates
        if identifier in seen:
            continue
        seen.add(identifier)

        # Check for fix/close keywords before the match
        start = match.start()
        prefix_text = text[max(0, start - 20) : start].lower().strip()
        is_closing = any(prefix_text.endswith(kw) for kw in FIX_KEYWORDS)

        # Filter by project prefixes if provided
        if input_data.project_prefixes:
            prefix_set = {p.upper() for p in input_data.project_prefixes}
            if project not in prefix_set:
                continue

        links.append(IssueLink(identifier=identifier, is_closing=is_closing))

    return CommitLinkerOutput(links=links, method="regex")


__all__ = ["generate_commit_linker"]
