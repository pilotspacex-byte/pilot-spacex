"""Skill-related DI provider sub-container.

Extracted from container.py to keep the main container under 700 lines.
Covers: role skill services, workspace role skill services, skill
concurrency, and user skill creation.

SkillContainer inherits InfraContainer so it can reference InfraContainer
repositories directly (e.g. skill_execution_repository).
"""

from __future__ import annotations

from dependency_injector import providers

from pilot_space.application.services.role_skill import (
    CreateRoleSkillService,
    DeleteRoleSkillService,
    GenerateRoleSkillService,
    ListRoleSkillsService,
    UpdateRoleSkillService,
)
from pilot_space.application.services.skill.concurrency_manager import SkillConcurrencyManager
from pilot_space.application.services.user_skill.create_user_skill_service import (
    CreateUserSkillService,
)
from pilot_space.application.services.workspace_role_skill import (
    ActivateWorkspaceSkillService,
    CreateWorkspaceSkillService,
    DeleteWorkspaceSkillService,
    ListWorkspaceSkillsService,
)
from pilot_space.container._base import InfraContainer
from pilot_space.dependencies.auth import get_current_session


class SkillContainer(InfraContainer):
    """DI sub-container for skill-related service providers.

    Inherits InfraContainer to reference repository providers.
    Container (main) inherits this class to compose all providers.
    """

    # ---------------------------------------------------------------------------
    # Role Skill Services
    # ---------------------------------------------------------------------------

    create_role_skill_service = providers.Factory(
        CreateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    update_role_skill_service = providers.Factory(
        UpdateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    delete_role_skill_service = providers.Factory(
        DeleteRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    list_role_skills_service = providers.Factory(
        ListRoleSkillsService,
        session=providers.Callable(get_current_session),
    )

    generate_role_skill_service = providers.Factory(
        GenerateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    # ---------------------------------------------------------------------------
    # Workspace Role Skill Services (WRSKL-01..02)
    # ---------------------------------------------------------------------------

    create_workspace_skill_service = providers.Factory(
        CreateWorkspaceSkillService,
        session=providers.Callable(get_current_session),
    )

    activate_workspace_skill_service = providers.Factory(
        ActivateWorkspaceSkillService,
        session=providers.Callable(get_current_session),
    )

    list_workspace_skills_service = providers.Factory(
        ListWorkspaceSkillsService,
        session=providers.Callable(get_current_session),
    )

    delete_workspace_skill_service = providers.Factory(
        DeleteWorkspaceSkillService,
        session=providers.Callable(get_current_session),
    )

    # ---------------------------------------------------------------------------
    # Skill Concurrency + Execution (T-044, T-045, T-047)
    # ---------------------------------------------------------------------------

    # Redis-backed concurrency manager — one per process
    skill_concurrency_manager = providers.Singleton(
        SkillConcurrencyManager,
        redis_client=InfraContainer.redis_client,
    )

    # ---------------------------------------------------------------------------
    # User Skill Service (P20-08)
    # NOTE: CreateUserSkillService is constructed imperatively in user_skills
    # router and does not use @inject. Registered here so endpoints can also
    # inject it via Depends() if needed.
    # ---------------------------------------------------------------------------

    create_user_skill_service = providers.Factory(
        CreateUserSkillService,
        session=providers.Callable(get_current_session),
    )


__all__ = ["SkillContainer"]
