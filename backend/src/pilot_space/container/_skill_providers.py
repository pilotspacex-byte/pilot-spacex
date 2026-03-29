"""Skill-related DI provider sub-container.

Extracted from container.py to keep the main container under 700 lines.
Covers: skill execution, skill concurrency, and user skill creation.

SkillContainer inherits InfraContainer so it can reference InfraContainer
repositories directly (e.g. skill_execution_repository, work_intent_repository).
"""

from __future__ import annotations

from dependency_injector import providers

from pilot_space.application.services.skill.concurrency_manager import SkillConcurrencyManager
from pilot_space.application.services.skill.graph_compiler_service import GraphCompilerService
from pilot_space.application.services.skill.graph_decompiler_service import GraphDecompilerService
from pilot_space.application.services.skill.marketplace_install_service import (
    MarketplaceInstallService,
)
from pilot_space.application.services.skill.marketplace_review_service import (
    MarketplaceReviewService,
)
from pilot_space.application.services.skill.marketplace_service import MarketplaceService
from pilot_space.application.services.skill.skill_execution_service import SkillExecutionService
from pilot_space.application.services.skill.skill_graph_service import SkillGraphService
from pilot_space.application.services.user_skill.create_user_skill_service import (
    CreateUserSkillService,
)
from pilot_space.container._base import InfraContainer
from pilot_space.dependencies.auth import get_current_session


class SkillContainer(InfraContainer):
    """DI sub-container for skill-related service providers.

    Inherits InfraContainer to reference repository providers.
    Container (main) inherits this class to compose all providers.
    """

    # ---------------------------------------------------------------------------
    # Skill Concurrency + Execution (T-044, T-045, T-047)
    # ---------------------------------------------------------------------------

    # Redis-backed concurrency manager — one per process
    skill_concurrency_manager = providers.Singleton(
        SkillConcurrencyManager,
        redis_client=InfraContainer.redis_client,
    )

    skill_execution_service = providers.Factory(
        SkillExecutionService,
        session=providers.Callable(get_current_session),
        skill_exec_repo=InfraContainer.skill_execution_repository,
        intent_repo=InfraContainer.work_intent_repository,
        concurrency_manager=skill_concurrency_manager,
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

    # ---------------------------------------------------------------------------
    # Skill Graph Service (P52-03)
    # ---------------------------------------------------------------------------

    skill_graph_service = providers.Factory(
        SkillGraphService,
        session=providers.Callable(get_current_session),
        repo=InfraContainer.skill_graph_repository,
    )

    # ---------------------------------------------------------------------------
    # Graph Compiler Service (P53-01)
    # ---------------------------------------------------------------------------

    graph_compiler_service = providers.Factory(
        GraphCompilerService,
        session=providers.Callable(get_current_session),
    )

    # ---------------------------------------------------------------------------
    # Graph Decompiler Service (P53-03)
    # ---------------------------------------------------------------------------

    graph_decompiler_service = providers.Factory(
        GraphDecompilerService,
        session=providers.Callable(get_current_session),
    )

    # ---------------------------------------------------------------------------
    # Marketplace Services (P54-04)
    # ---------------------------------------------------------------------------

    marketplace_service = providers.Factory(
        MarketplaceService,
        session=providers.Callable(get_current_session),
    )

    marketplace_install_service = providers.Factory(
        MarketplaceInstallService,
        session=providers.Callable(get_current_session),
    )

    marketplace_review_service = providers.Factory(
        MarketplaceReviewService,
        session=providers.Callable(get_current_session),
    )


__all__ = ["SkillContainer"]
