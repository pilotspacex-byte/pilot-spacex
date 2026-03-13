"""Fixtures for performance benchmark tests."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


@pytest.fixture
def test_note() -> AsyncMock:
    """Lightweight mock note for benchmark URL construction.

    Performance tests only need ``test_note.id`` to build request paths.
    They mock the underlying agent, so no real DB object is needed.
    """
    mock = AsyncMock()
    mock.id = uuid4()
    return mock


@pytest.fixture
def test_issue() -> AsyncMock:
    """Lightweight mock issue for benchmark URL construction.

    Performance tests only need ``test_issue.id`` to build request paths.
    They mock the underlying agent, so no real DB object is needed.
    """
    mock = AsyncMock()
    mock.id = uuid4()
    return mock
