"""Unit tests for DocumentIngestionHandler.

Covers KG-01 through KG-04:
- KG-01: Happy path — DOCUMENT + DOCUMENT_CHUNK nodes created via background queue
- KG-02: DOCUMENT_CHUNK properties include heading, chunk_index, parent_document_id, project_id
- KG-03: RELATES_TO edges created when similarity >= 0.75; not created when < 0.75
- KG-04: OCR-extracted text used when available; binary without extraction returns ACK-able error
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.embedding_service import EmbeddingConfig, EmbeddingService
from pilot_space.domain.graph_node import NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.queue.handlers.document_ingestion_handler import (
    TASK_DOCUMENT_INGESTION,
    DocumentIngestionHandler,
)

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = uuid4()
_PROJECT_ID = uuid4()
_ATTACHMENT_ID = uuid4()


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


def _make_embedding_service(embed_return: list[float] | None = None) -> EmbeddingService:
    svc = EmbeddingService(EmbeddingConfig(openai_api_key=None))
    svc.embed = AsyncMock(return_value=embed_return)  # type: ignore[method-assign]
    return svc


def _make_scored_node(score: float = 0.9, project_id: UUID | None = None) -> ScoredNode:
    from pilot_space.domain.graph_node import GraphNode

    node = MagicMock(spec=GraphNode)
    node.id = uuid4()
    node.properties = {"project_id": str(project_id or _PROJECT_ID)}
    sn = MagicMock(spec=ScoredNode)
    sn.score = score
    sn.node = node
    return sn


def _make_payload(
    attachment_id: UUID | None = None,
    workspace_id: UUID | None = None,
    project_id: UUID | None = None,
) -> dict:
    return {
        "task_type": TASK_DOCUMENT_INGESTION,
        "workspace_id": str(workspace_id or _WORKSPACE_ID),
        "project_id": str(project_id or _PROJECT_ID),
        "attachment_id": str(attachment_id or _ATTACHMENT_ID),
        "actor_user_id": "00000000-0000-0000-0000-000000000001",
    }


# ---------------------------------------------------------------------------
# KG-01: happy path — DOCUMENT + DOCUMENT_CHUNK nodes created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_happy_path() -> None:
    """KG-01: handle() creates DOCUMENT node + DOCUMENT_CHUNK nodes; returns success."""
    session = _make_session()
    embedding_svc = _make_embedding_service(embed_return=[0.1] * 768)

    write_results = [
        MagicMock(node_ids=[uuid4()]),  # DOCUMENT node result
        MagicMock(node_ids=[uuid4(), uuid4()]),  # DOCUMENT_CHUNK nodes result
    ]

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(return_value=("# Hello\n\nWorld content here", "raw")),
        ),
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.ChatAttachment"
        ) as MockAttachment,
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "hello.txt"
        mock_attachment.mime_type = "text/plain"
        mock_attachment.size_bytes = 1024
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        mock_write_instance = AsyncMock()
        mock_write_instance.execute = AsyncMock(side_effect=write_results)
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        mock_repo.hybrid_search = AsyncMock(return_value=[])
        mock_repo.upsert_edge = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session,
            embedding_service=embedding_svc,
            queue=None,
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is True
    assert "node_ids" in result
    assert result["chunks"] > 0
    # GraphWriteService.execute called at least twice: DOCUMENT node + DOCUMENT_CHUNK nodes
    assert mock_write_instance.execute.call_count >= 2


# ---------------------------------------------------------------------------
# KG-02: DOCUMENT_CHUNK properties contain required metadata fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chunk_properties() -> None:
    """KG-02: DOCUMENT_CHUNK NodeInput properties contain chunk_index, heading, parent_document_id, project_id."""
    from pilot_space.application.services.memory.graph_write_service import NodeInput

    session = _make_session()
    embedding_svc = _make_embedding_service()
    captured_chunk_inputs: list[NodeInput] = []

    async def _capture_execute(payload):
        for node_input in payload.nodes:
            if node_input.node_type == NodeType.DOCUMENT_CHUNK:
                captured_chunk_inputs.append(node_input)
        return MagicMock(node_ids=[uuid4()])

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(
                return_value=(
                    "# Section One\n\nContent for chunk one.\n\n# Section Two\n\nContent for chunk two.",
                    "ocr",
                )
            ),
        ),
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "doc.pdf"
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.size_bytes = 2048
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        mock_write_instance = AsyncMock()
        mock_write_instance.execute = AsyncMock(side_effect=_capture_execute)
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        mock_repo.hybrid_search = AsyncMock(return_value=[])
        mock_repo.upsert_edge = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session, embedding_service=embedding_svc, queue=None
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is True
    assert len(captured_chunk_inputs) > 0, "Expected at least one DOCUMENT_CHUNK node"
    for chunk_input in captured_chunk_inputs:
        props = chunk_input.properties
        assert "chunk_index" in props, "chunk_index missing from DOCUMENT_CHUNK properties"
        assert "heading" in props, "heading missing from DOCUMENT_CHUNK properties"
        assert "parent_document_id" in props, (
            "parent_document_id missing from DOCUMENT_CHUNK properties"
        )
        assert "project_id" in props, "project_id missing from DOCUMENT_CHUNK properties"
        assert props["parent_document_id"] == str(_ATTACHMENT_ID)
        assert props["project_id"] == str(_PROJECT_ID)
        # chunk_index must not be set on chunk nodes (Pitfall 3: no external_id on chunks)
        assert chunk_input.external_id is None, (
            "external_id must NOT be set on DOCUMENT_CHUNK nodes"
        )


# ---------------------------------------------------------------------------
# KG-03: RELATES_TO edges created when similarity >= 0.75
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_similarity_edges() -> None:
    """KG-03: RELATES_TO edge is created when similar node score >= 0.75."""
    session = _make_session()
    embedding_svc = _make_embedding_service(embed_return=[0.1] * 768)

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(return_value=("# Content\n\nSome text.", "office")),
        ),
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "spec.docx"
        mock_attachment.mime_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        mock_attachment.size_bytes = 4096
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        similar_node = _make_scored_node(score=0.9)
        mock_write_instance = AsyncMock()
        mock_write_instance.execute = AsyncMock(return_value=MagicMock(node_ids=[uuid4()]))
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        mock_repo.hybrid_search = AsyncMock(return_value=[similar_node])
        mock_repo.upsert_edge = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session, embedding_service=embedding_svc, queue=None
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is True
    assert result["edges"] >= 1
    mock_repo.upsert_edge.assert_called()


@pytest.mark.asyncio
async def test_similarity_below_threshold() -> None:
    """KG-03: No RELATES_TO edge when similarity score < 0.75."""
    session = _make_session()
    embedding_svc = _make_embedding_service(embed_return=[0.1] * 768)

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(return_value=("# Content\n\nSome text.", "raw")),
        ),
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "notes.txt"
        mock_attachment.mime_type = "text/plain"
        mock_attachment.size_bytes = 512
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        low_score_node = _make_scored_node(score=0.5)
        mock_write_instance = AsyncMock()
        mock_write_instance.execute = AsyncMock(return_value=MagicMock(node_ids=[uuid4()]))
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        mock_repo.hybrid_search = AsyncMock(return_value=[low_score_node])
        mock_repo.upsert_edge = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session, embedding_service=embedding_svc, queue=None
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is True
    assert result["edges"] == 0
    mock_repo.upsert_edge.assert_not_called()


# ---------------------------------------------------------------------------
# KG-04: Text source resolution — OCR preferred; binary without extraction → skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_source_ocr() -> None:
    """KG-04: OCR result text is used when available (extraction_source = "ocr")."""
    from pilot_space.application.services.memory.graph_write_service import NodeInput

    session = _make_session()
    embedding_svc = _make_embedding_service()
    captured_document_inputs: list[NodeInput] = []

    async def _capture_execute(payload):
        for node_input in payload.nodes:
            if node_input.node_type == NodeType.DOCUMENT:
                captured_document_inputs.append(node_input)
        return MagicMock(node_ids=[uuid4()])

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(return_value=("OCR extracted text here", "ocr")),
        ),
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "scan.pdf"
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.size_bytes = 8192
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        mock_write_instance = AsyncMock()
        mock_write_instance.execute = AsyncMock(side_effect=_capture_execute)
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        mock_repo.hybrid_search = AsyncMock(return_value=[])
        mock_repo.upsert_edge = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session, embedding_service=embedding_svc, queue=None
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is True
    assert len(captured_document_inputs) == 1
    doc_props = captured_document_inputs[0].properties
    assert doc_props["extraction_source"] == "ocr"


@pytest.mark.asyncio
async def test_binary_no_extraction() -> None:
    """KG-04: Binary MIME with no extracted text returns ACK-able error (no GraphWriteService call)."""
    session = _make_session()
    embedding_svc = _make_embedding_service()

    with (
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.GraphWriteService"
        ) as MockWriteService,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.KnowledgeGraphRepository"
        ) as MockRepo,
        patch(
            "pilot_space.infrastructure.queue.handlers.document_ingestion_handler._resolve_extracted_text",
            new=AsyncMock(return_value=None),  # None = binary, no extraction
        ),
    ):
        mock_attachment = MagicMock()
        mock_attachment.filename = "photo.jpg"
        mock_attachment.mime_type = "image/jpeg"
        mock_attachment.size_bytes = 2000000
        mock_attachment.workspace_id = _WORKSPACE_ID
        session.get.return_value = mock_attachment

        mock_write_instance = AsyncMock()
        MockWriteService.return_value = mock_write_instance

        mock_repo = AsyncMock()
        MockRepo.return_value = mock_repo

        handler = DocumentIngestionHandler(
            session=session, embedding_service=embedding_svc, queue=None
        )
        result = await handler.handle(_make_payload())

    assert result["success"] is False
    assert result.get("reason") == "no_text_available"
    mock_write_instance.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Invalid payload guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_payload() -> None:
    """Bad payload returns {success: False} — worker ACKs without retry."""
    session = _make_session()
    handler = DocumentIngestionHandler(
        session=session, embedding_service=_make_embedding_service(), queue=None
    )
    result = await handler.handle({"task_type": "document_ingestion"})  # missing required fields
    assert result["success"] is False
