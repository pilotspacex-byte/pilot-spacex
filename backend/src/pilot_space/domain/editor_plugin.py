"""EditorPlugin domain re-export.

Provides domain-layer access to the EditorPlugin SQLAlchemy model
for the editor plugin system (Phase 45, PLUG-01..03).

Editor plugins are JS bundles with a manifest (name, version, permissions,
blockTypes, slashCommands, actions). They are distinct from workspace_plugins
(Phase 19 -- GitHub-sourced skill plugins).
"""

from pilot_space.infrastructure.database.models.editor_plugin import EditorPlugin

__all__ = ["EditorPlugin"]
