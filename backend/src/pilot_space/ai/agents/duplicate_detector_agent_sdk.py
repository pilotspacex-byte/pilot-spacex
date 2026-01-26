"""Duplicate Detector Agent (SDK) for finding similar issues.

T131: Create DuplicateDetectorAgent with pgvector similarity search.
Migrated to Claude Agent SDK pattern with SDKBaseAgent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    SDKBaseAgent,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class DuplicateDetectionInput:
    """Input for duplicate detection.

    Attributes:
        title: Issue title to check.
        description: Issue description (optional).
        project_id: Project to search within.
        workspace_id: Workspace scope.
        exclude_issue_id: Issue ID to exclude (for updates).
        threshold: Minimum similarity score (0-1).
        max_results: Maximum duplicates to return.
    """

    title: str
    workspace_id: UUID
    project_id: UUID | None = None
    description: str | None = None
    exclude_issue_id: UUID | None = None
    threshold: float = 0.75
    max_results: int = 5


@dataclass
class DuplicateCandidate:
    """A potential duplicate issue.

    Attributes:
        issue_id: UUID of the potential duplicate.
        identifier: Human-readable identifier (e.g., PILOT-123).
        title: Issue title.
        similarity: Similarity score (0-1).
        explanation: Brief explanation of why it's similar.
    """

    issue_id: UUID
    identifier: str
    title: str
    similarity: float
    explanation: str | None = None


@dataclass
class DuplicateDetectionOutput:
    """Output from duplicate detection.

    Attributes:
        candidates: List of potential duplicates.
        has_likely_duplicate: Whether any candidate exceeds high confidence threshold.
        highest_similarity: Highest similarity score found.
    """

    candidates: list[DuplicateCandidate] = field(default_factory=list)
    has_likely_duplicate: bool = False
    highest_similarity: float = 0.0


class DuplicateDetectorAgent(
    SDKBaseAgent[DuplicateDetectionInput, DuplicateDetectionOutput]
):
    """Agent for detecting duplicate issues using vector similarity.

    Uses OpenAI embeddings + pgvector for efficient similarity search.
    Falls back to text-based matching if embeddings unavailable.

    Threshold recommendations:
    - 0.9+: Very likely duplicate
    - 0.8-0.9: Possible duplicate, review recommended
    - 0.75-0.8: Related issue

    Architecture:
    - Extends SDKBaseAgent for infrastructure access
    - Uses OpenAI for embeddings (per DD-011)
    - Queries pgvector for cosine similarity
    - Returns ranked candidates with explanations
    """

    AGENT_NAME = "duplicate_detector"
    DEFAULT_MODEL = "text-embedding-3-small"  # OpenAI embedding model
    EMBEDDING_DIMENSIONS = 1536

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
        session: AsyncSession,
        model: str | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure key storage for API key retrieval
            session: Database session for vector queries
            model: Override embedding model (defaults to text-embedding-3-small)
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage
        self._session = session
        self._model = model or self.DEFAULT_MODEL

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for embeddings.

        Returns:
            Tuple of ("openai", model_name) per DD-011 routing.
        """
        return ("openai", self._model)

    def _validate_input(self, input_data: DuplicateDetectionInput) -> None:
        """Validate input data.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.title or not input_data.title.strip():
            raise ValueError("Issue title is required for duplicate detection")
        if input_data.threshold < 0 or input_data.threshold > 1:
            raise ValueError("Threshold must be between 0 and 1")
        if input_data.max_results <= 0:
            raise ValueError("max_results must be positive")

    async def execute(
        self,
        input_data: DuplicateDetectionInput,
        context: AgentContext,
    ) -> DuplicateDetectionOutput:
        """Execute duplicate detection.

        Args:
            input_data: Issue content to check.
            context: Agent execution context.

        Returns:
            DuplicateDetectionOutput with ranked candidates.

        Raises:
            ValueError: If input validation fails.
            RuntimeError: If OpenAI API key is missing.
        """
        # Validate input
        self._validate_input(input_data)

        # Combine title and description for embedding
        text_to_embed = input_data.title
        if input_data.description:
            text_to_embed = f"{input_data.title}\n\n{input_data.description}"

        # Get OpenAI API key from secure storage
        api_key = await self._key_storage.get_api_key(
            workspace_id=context.workspace_id,
            provider="openai",
        )
        if not api_key:
            raise RuntimeError(
                f"OpenAI API key not found for workspace {context.workspace_id}"
            )

        # Generate embedding using OpenAI
        embedding, input_tokens = await self._generate_embedding(text_to_embed, api_key)

        # Track embedding usage (no output tokens for embeddings)
        await self.track_usage(
            context=context,
            input_tokens=input_tokens,
            output_tokens=0,
        )

        # Search for similar issues using pgvector
        candidates = await self._search_similar_issues(
            embedding=embedding,
            workspace_id=input_data.workspace_id,
            project_id=input_data.project_id,
            exclude_issue_id=input_data.exclude_issue_id,
            threshold=input_data.threshold,
            max_results=input_data.max_results,
        )

        # Determine if likely duplicate exists
        has_likely_duplicate = any(c.similarity >= 0.85 for c in candidates)
        highest_similarity = max((c.similarity for c in candidates), default=0.0)

        return DuplicateDetectionOutput(
            candidates=candidates,
            has_likely_duplicate=has_likely_duplicate,
            highest_similarity=highest_similarity,
        )

    async def _generate_embedding(
        self,
        text: str,
        api_key: str,
    ) -> tuple[list[float], int]:
        """Generate embedding using OpenAI.

        Args:
            text: Text to embed.
            api_key: OpenAI API key.

        Returns:
            Tuple of (embedding vector, input tokens used).

        Raises:
            Exception: If OpenAI API call fails.
        """
        import openai

        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.embeddings.create(
            model=self._model,
            input=text,
            dimensions=self.EMBEDDING_DIMENSIONS,
        )

        embedding = response.data[0].embedding
        input_tokens = response.usage.total_tokens

        return embedding, input_tokens

    async def _search_similar_issues(
        self,
        embedding: list[float],
        workspace_id: UUID,
        project_id: UUID | None,
        exclude_issue_id: UUID | None,
        threshold: float,
        max_results: int,
    ) -> list[DuplicateCandidate]:
        """Search for similar issues using pgvector.

        Args:
            embedding: Query embedding vector.
            workspace_id: Workspace scope.
            project_id: Optional project filter.
            exclude_issue_id: Issue to exclude.
            threshold: Minimum similarity.
            max_results: Max results.

        Returns:
            List of duplicate candidates sorted by similarity.
        """
        from sqlalchemy import and_, select, text

        from pilot_space.infrastructure.database.models import (
            Embedding,
            EmbeddingType,
            Issue,
        )

        # Build vector literal for pgvector
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        # Query using cosine similarity
        # 1 - (embedding <=> query_vector) gives similarity (pgvector uses distance)
        similarity_expr = text(
            f"1 - (embedding <=> '{vector_str}'::vector)"
        ).label("similarity")

        query = (
            select(
                Embedding.content_id,
                Embedding.content_preview,
                Embedding.embedding_metadata,
                similarity_expr,
            )
            .where(
                and_(
                    Embedding.workspace_id == workspace_id,
                    Embedding.content_type == EmbeddingType.ISSUE,
                    Embedding.is_deleted == False,  # noqa: E712
                    text(
                        f"1 - (embedding <=> '{vector_str}'::vector) >= {threshold}"
                    ),
                )
            )
        )

        if project_id:
            query = query.where(Embedding.project_id == project_id)

        if exclude_issue_id:
            query = query.where(Embedding.content_id != exclude_issue_id)

        query = query.order_by(text("similarity DESC")).limit(max_results)

        result = await self._session.execute(query)
        rows = result.all()

        # Build candidates with issue details
        candidates: list[DuplicateCandidate] = []
        for row in rows:
            content_id = row[0]
            # row[1] is content_preview, row[2] is metadata - reserved for future use
            similarity = float(row[3])

            # Get issue details
            issue_query = select(Issue).where(Issue.id == content_id)
            issue_result = await self._session.execute(issue_query)
            issue = issue_result.scalar_one_or_none()

            if issue:
                candidates.append(
                    DuplicateCandidate(
                        issue_id=issue.id,
                        identifier=issue.identifier,
                        title=issue.name,
                        similarity=similarity,
                        explanation=self._generate_explanation(similarity),
                    )
                )

        return candidates

    def _generate_explanation(self, similarity: float) -> str:
        """Generate explanation for similarity score.

        Args:
            similarity: Similarity score (0-1).

        Returns:
            Human-readable explanation.
        """
        if similarity >= 0.95:
            return "Very high similarity - likely exact duplicate"
        if similarity >= 0.9:
            return "High similarity - likely duplicate or closely related"
        if similarity >= 0.85:
            return "Significant similarity - may be duplicate or related"
        if similarity >= 0.8:
            return "Moderate similarity - possibly related issue"
        return "Some similarity - review for potential relationship"


__all__ = [
    "DuplicateCandidate",
    "DuplicateDetectionInput",
    "DuplicateDetectionOutput",
    "DuplicateDetectorAgent",
]
