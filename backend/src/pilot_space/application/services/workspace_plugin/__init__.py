"""Workspace plugin services.

- InstallPluginService: install, update, uninstall plugins
- SeedPluginsService: seed new workspaces with default plugins
"""

from pilot_space.application.services.workspace_plugin.install_plugin_service import (
    InstallPluginService,
)
from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
    SeedPluginsService,
)

__all__ = ["InstallPluginService", "SeedPluginsService"]
