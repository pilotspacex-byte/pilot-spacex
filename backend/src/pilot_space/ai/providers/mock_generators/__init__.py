"""Mock response generators for each AI agent.

Import this module to register all mock generators with MockResponseRegistry.
Generators are auto-registered via the @MockResponseRegistry.register decorator.

Usage:
    # Import to register all generators
    import pilot_space.ai.providers.mock_generators  # noqa: F401

    # Then use MockProvider
    mock_provider = MockProvider.get_instance()
    if mock_provider.is_enabled():
        result = await mock_provider.execute(agent, input_data, context)
"""

# Import all generators to trigger registration
from pilot_space.ai.providers.mock_generators.ai_context import (
    generate_ai_context as _ai_context,
)
from pilot_space.ai.providers.mock_generators.assignee_recommender import (
    generate_assignee_recommendation as _assignee_recommender,
)
from pilot_space.ai.providers.mock_generators.commit_linker import (
    generate_commit_linker as _commit_linker,
)
from pilot_space.ai.providers.mock_generators.conversation import (
    generate_conversation as _conversation,
)
from pilot_space.ai.providers.mock_generators.duplicate_detector import (
    generate_duplicate_detection as _duplicate_detector,
)
from pilot_space.ai.providers.mock_generators.ghost_text import (
    generate_ghost_text as _ghost_text,
)
from pilot_space.ai.providers.mock_generators.issue_enhancer import (
    generate_issue_enhancement as _issue_enhancer,
)
from pilot_space.ai.providers.mock_generators.issue_extractor import (
    generate_issue_extraction as _issue_extractor,
)
from pilot_space.ai.providers.mock_generators.margin_annotation import (
    generate_margin_annotation as _margin_annotation,
)
from pilot_space.ai.providers.mock_generators.pr_review import (
    generate_pr_review as _pr_review,
)

# Suppress unused import warnings
_ = (
    _ghost_text,
    _issue_enhancer,
    _margin_annotation,
    _issue_extractor,
    _conversation,
    _assignee_recommender,
    _duplicate_detector,
    _commit_linker,
    _ai_context,
    _pr_review,
)

__all__: list[str] = []
