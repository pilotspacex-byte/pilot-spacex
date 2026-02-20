"""Type aliases for repository dependency injection.

Extracted from dependencies.py to respect the 700-line file limit.
Same pattern: @inject wrapper + Annotated[T, Depends()] type alias.
"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from pilot_space.container import Container
from pilot_space.infrastructure.database.repositories.activity_repository import (
    ActivityRepository,
)
from pilot_space.infrastructure.database.repositories.cycle_repository import (
    CycleRepository,
)
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.note_issue_link_repository import (
    NoteIssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_note_link_repository import (
    NoteNoteLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.database.repositories.note_yjs_state_repository import (
    NoteYjsStateRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)


@inject
def _get_activity_repository(
    repo: ActivityRepository = Depends(Provide[Container.activity_repository]),
) -> ActivityRepository:
    return repo


ActivityRepositoryDep = Annotated[ActivityRepository, Depends(_get_activity_repository)]


@inject
def _get_cycle_repository(
    repo: CycleRepository = Depends(Provide[Container.cycle_repository]),
) -> CycleRepository:
    return repo


CycleRepositoryDep = Annotated[CycleRepository, Depends(_get_cycle_repository)]


@inject
def _get_invitation_repository(
    repo: InvitationRepository = Depends(Provide[Container.invitation_repository]),
) -> InvitationRepository:
    return repo


InvitationRepositoryDep = Annotated[InvitationRepository, Depends(_get_invitation_repository)]


@inject
def _get_issue_repository(
    repo: IssueRepository = Depends(Provide[Container.issue_repository]),
) -> IssueRepository:
    return repo


IssueRepositoryDep = Annotated[IssueRepository, Depends(_get_issue_repository)]


@inject
def _get_note_issue_link_repository(
    repo: NoteIssueLinkRepository = Depends(Provide[Container.note_issue_link_repository]),
) -> NoteIssueLinkRepository:
    return repo


NoteIssueLinkRepositoryDep = Annotated[
    NoteIssueLinkRepository, Depends(_get_note_issue_link_repository)
]


@inject
def _get_note_note_link_repository(
    repo: NoteNoteLinkRepository = Depends(Provide[Container.note_note_link_repository]),
) -> NoteNoteLinkRepository:
    return repo


NoteNoteLinkRepositoryDep = Annotated[
    NoteNoteLinkRepository, Depends(_get_note_note_link_repository)
]


@inject
def _get_note_repository(
    repo: NoteRepository = Depends(Provide[Container.note_repository]),
) -> NoteRepository:
    return repo


NoteRepositoryDep = Annotated[NoteRepository, Depends(_get_note_repository)]


@inject
def _get_note_yjs_state_repository(
    repo: NoteYjsStateRepository = Depends(Provide[Container.note_yjs_state_repository]),
) -> NoteYjsStateRepository:
    return repo


NoteYjsStateRepositoryDep = Annotated[
    NoteYjsStateRepository, Depends(_get_note_yjs_state_repository)
]


@inject
def _get_project_repository(
    repo: ProjectRepository = Depends(Provide[Container.project_repository]),
) -> ProjectRepository:
    return repo


ProjectRepositoryDep = Annotated[ProjectRepository, Depends(_get_project_repository)]


@inject
def _get_user_repository(
    repo: UserRepository = Depends(Provide[Container.user_repository]),
) -> UserRepository:
    return repo


UserRepositoryDep = Annotated[UserRepository, Depends(_get_user_repository)]


@inject
def _get_workspace_repository(
    repo: WorkspaceRepository = Depends(Provide[Container.workspace_repository]),
) -> WorkspaceRepository:
    return repo


WorkspaceRepositoryDep = Annotated[WorkspaceRepository, Depends(_get_workspace_repository)]

__all__ = [
    "ActivityRepositoryDep",
    "CycleRepositoryDep",
    "InvitationRepositoryDep",
    "IssueRepositoryDep",
    "NoteIssueLinkRepositoryDep",
    "NoteNoteLinkRepositoryDep",
    "NoteRepositoryDep",
    "NoteYjsStateRepositoryDep",
    "ProjectRepositoryDep",
    "UserRepositoryDep",
    "WorkspaceRepositoryDep",
]
