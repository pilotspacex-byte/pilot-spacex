"""Spaces module for sandboxed agent execution environments.

Provides abstractions for managing user workspaces where Claude Agent SDK
operates with filesystem isolation. Supports both local (MVP) and
container-based (scale) deployments.

Reference: docs/architect/scalable-agent-architecture.md
"""

from pilot_space.spaces.base import (
    SpaceContext,
    SpaceError,
    SpaceInterface,
    SpacePreparationError,
)
from pilot_space.spaces.bootstrapper import ProjectBootstrapper
from pilot_space.spaces.local import LocalFileSystemSpace
from pilot_space.spaces.manager import SpaceManager

__all__ = [
    "LocalFileSystemSpace",
    "ProjectBootstrapper",
    "SpaceContext",
    "SpaceError",
    "SpaceInterface",
    "SpaceManager",
    "SpacePreparationError",
]
