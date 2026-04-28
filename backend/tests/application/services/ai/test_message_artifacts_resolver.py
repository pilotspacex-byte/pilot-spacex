"""Phase 87.1 Plan 03 — MessageArtifactsResolver unit tests.

The resolver maps a list of message ``metadata.artifact_ids`` lookups
into per-message ``InlineArtifactRefSchema`` lists. It batch-fetches via
the repository (single SELECT WHERE id = ANY(...) AND workspace_id = ...
AND is_deleted = false AND status = 'ready'), filters cross-workspace
ids out, and derives ``type`` from the filename extension.

These tests use a fake repo so they run on the default SQLite db_session
fixture per .claude/rules/testing.md (no PostgreSQL features required).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.ai.message_artifacts_resolver import (
    MessageArtifactsResolver,
    ResolveArtifactsPayload,
)


class _FakeArtifact:
    def __init__(
        self,
        *,
        id: UUID,
        workspace_id: UUID,
        filename: str,
        is_deleted: bool = False,
        status: str = "ready",
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.workspace_id = workspace_id
        self.filename = filename
        self.is_deleted = is_deleted
        self.status = status
        self.updated_at = updated_at or datetime(2026, 4, 28, 10, 0, tzinfo=UTC)


class _FakeRepo:
    """Minimal stand-in for ArtifactRepository with a batch fetch method."""

    def __init__(self, rows: list[_FakeArtifact]) -> None:
        self._rows = rows
        self.last_call: dict[str, Any] | None = None

    async def list_by_ids_for_workspace(
        self,
        ids: list[UUID],
        workspace_id: UUID,
    ) -> list[_FakeArtifact]:
        self.last_call = {"ids": list(ids), "workspace_id": workspace_id}
        result = [
            r
            for r in self._rows
            if r.id in set(ids)
            and r.workspace_id == workspace_id
            and not r.is_deleted
            and r.status == "ready"
        ]
        return result


@pytest.mark.asyncio
class TestMessageArtifactsResolver:
    async def test_returns_empty_for_message_without_metadata(self) -> None:
        ws = uuid4()
        resolver = MessageArtifactsResolver(repo=_FakeRepo([]))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={uuid4(): None},
            )
        )
        assert out == {}

    async def test_resolves_md_artifact_to_inline_ref(self) -> None:
        ws = uuid4()
        artifact_id = uuid4()
        msg_id = uuid4()
        rows = [
            _FakeArtifact(
                id=artifact_id,
                workspace_id=ws,
                filename="report.md",
            )
        ]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(artifact_id)]}},
            )
        )
        assert msg_id in out
        refs = out[msg_id]
        assert len(refs) == 1
        assert refs[0].id == artifact_id
        assert refs[0].type == "MD"
        assert refs[0].title == "report.md"
        assert refs[0].updated_at is not None

    async def test_resolves_html_artifact(self) -> None:
        ws = uuid4()
        artifact_id = uuid4()
        msg_id = uuid4()
        rows = [_FakeArtifact(id=artifact_id, workspace_id=ws, filename="page.html")]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(artifact_id)]}},
            )
        )
        assert out[msg_id][0].type == "HTML"
        assert out[msg_id][0].title == "page.html"

    async def test_drops_cross_workspace_artifact(self) -> None:
        ws = uuid4()
        other_ws = uuid4()
        artifact_id = uuid4()
        msg_id = uuid4()
        rows = [
            _FakeArtifact(id=artifact_id, workspace_id=other_ws, filename="leak.md"),
        ]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(artifact_id)]}},
            )
        )
        # Cross-workspace id is silently dropped (T-87.1-03-01).
        assert msg_id not in out or out[msg_id] == []

    async def test_drops_deleted_artifact(self) -> None:
        ws = uuid4()
        a_id = uuid4()
        msg_id = uuid4()
        rows = [
            _FakeArtifact(
                id=a_id,
                workspace_id=ws,
                filename="del.md",
                is_deleted=True,
            )
        ]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(a_id)]}},
            )
        )
        assert msg_id not in out or out[msg_id] == []

    async def test_drops_pending_upload_artifact(self) -> None:
        ws = uuid4()
        a_id = uuid4()
        msg_id = uuid4()
        rows = [
            _FakeArtifact(
                id=a_id,
                workspace_id=ws,
                filename="x.md",
                status="pending_upload",
            )
        ]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(a_id)]}},
            )
        )
        assert msg_id not in out or out[msg_id] == []

    async def test_caps_artifact_ids_per_message(self) -> None:
        ws = uuid4()
        msg_id = uuid4()
        ids = [uuid4() for _ in range(80)]
        # Repo only has the first 50 — but resolver MUST cap before query
        # so the repo is never asked about more than 50.
        rows = [
            _FakeArtifact(id=i, workspace_id=ws, filename="a.md") for i in ids[:50]
        ]
        repo = _FakeRepo(rows)
        resolver = MessageArtifactsResolver(repo=repo)
        await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={
                    msg_id: {"artifact_ids": [str(i) for i in ids]}
                },
            )
        )
        assert repo.last_call is not None
        assert len(repo.last_call["ids"]) <= 50

    async def test_skips_invalid_uuid_strings(self) -> None:
        ws = uuid4()
        msg_id = uuid4()
        a_id = uuid4()
        rows = [_FakeArtifact(id=a_id, workspace_id=ws, filename="ok.md")]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={
                    msg_id: {"artifact_ids": ["not-a-uuid", str(a_id)]}
                },
            )
        )
        assert len(out[msg_id]) == 1
        assert out[msg_id][0].id == a_id

    async def test_ignores_unknown_extension(self) -> None:
        """Filename with no md/html extension is not exposed.

        The InlineArtifactRef.type contract requires an ArtifactTokenKey.
        Unknown extensions are silently dropped rather than emitting
        garbage that the frontend cannot render.
        """
        ws = uuid4()
        a_id = uuid4()
        msg_id = uuid4()
        rows = [_FakeArtifact(id=a_id, workspace_id=ws, filename="weird.xyz")]
        resolver = MessageArtifactsResolver(repo=_FakeRepo(rows))
        out = await resolver.resolve(
            ResolveArtifactsPayload(
                workspace_id=ws,
                metadata_by_message_id={msg_id: {"artifact_ids": [str(a_id)]}},
            )
        )
        assert msg_id not in out or out[msg_id] == []
