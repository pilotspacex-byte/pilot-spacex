"""Duplicate Detector Agent for finding similar issues.

T131: Create DuplicateDetectorAgent with pgvector similarity search.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.telemetry import AIOperation

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

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


class DuplicateDetectorAgent(BaseAgent[DuplicateDetectionInput, DuplicateDetectionOutput]):
    """Agent for detecting duplicate issues using vector similarity.

    Uses OpenAI embeddings + pgvector for efficient similarity search.
    Falls back to text-based matching if embeddings unavailable.

    Threshold recommendations:
    - 0.9+: Very likely duplicate
    - 0.8-0.9: Possible duplicate, review recommended
    - 0.75-0.8: Related issue
    """

    task_type = TaskType.EMBEDDINGS
    operation = AIOperation.EMBEDDING

    def __init__(
        self,
        session: AsyncSession,
        model: str | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            session: Database session for vector queries.
            model: Override embedding model.
        """
        super().__init__(model)
        self._session = session

    async def _execute_impl(
        self,
        input_data: DuplicateDetectionInput,
        context: AgentContext,
    ) -> AgentResult[DuplicateDetectionOutput]:
        """Execute duplicate detection.

        Args:
            input_data: Issue content to check.
            context: Agent execution context.

        Returns:
            AgentResult with duplicate candidates.
        """
        # Combine title and description for embedding
        text_to_embed = input_data.title
        if input_data.description:
            text_to_embed = f"{input_data.title}\n\n{input_data.description}"

        # Generate embedding using OpenAI
        api_key = context.require_api_key(Provider.OPENAI)
        embedding = await self._generate_embedding(text_to_embed, api_key)

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

        return AgentResult(
            output=DuplicateDetectionOutput(
                candidates=candidates,
                has_likely_duplicate=has_likely_duplicate,
                highest_similarity=highest_similarity,
            ),
            input_tokens=len(text_to_embed.split()),  # Approximate
            output_tokens=0,
            model=self.model,
            provider=self.provider,
        )

    async def _generate_embedding(
        self,
        text: str,
        api_key: str,
    ) -> list[float]:
        """Generate embedding using OpenAI.

        Args:
            text: Text to embed.
            api_key: OpenAI API key.

        Returns:
            Embedding vector.
        """
        import openai

        client = openai.OpenAI(api_key=api_key)

        response = client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=1536,
        )

        return response.data[0].embedding

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
            List of duplicate candidates.
        """
        from sqlalchemy import and_, select, text

        from pilot_space.infrastructure.database.models import Embedding, EmbeddingType, Issue

        # Build vector literal for pgvector
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        # Query using cosine similarity
        # 1 - (embedding <=> query_vector) gives similarity (pgvector uses distance)
        similarity_expr = text(f"1 - (embedding <=> '{vector_str}'::vector)").label("similarity")

        query = select(
            Embedding.content_id,
            Embedding.content_preview,
            Embedding.embedding_metadata,
            similarity_expr,
        ).where(
            and_(
                Embedding.workspace_id == workspace_id,
                Embedding.content_type == EmbeddingType.ISSUE,
                Embedding.is_deleted == False,  # noqa: E712
                text(f"1 - (embedding <=> '{vector_str}'::vector) >= {threshold}"),
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
            similarity: Similarity score.

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

    def validate_input(self, input_data: DuplicateDetectionInput) -> None:
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


__all__ = [
    "DuplicateCandidate",
    "DuplicateDetectionInput",
    "DuplicateDetectionOutput",
    "DuplicateDetectorAgent",
]
