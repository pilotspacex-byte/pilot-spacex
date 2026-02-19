"""Intent service dependency injection type aliases.

Separated from dependencies.py to keep file size within the 700-line limit.
"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from pilot_space.application.services.intent import IntentDetectionService, IntentService
from pilot_space.container.container import Container

# ===== Intent Service Dependencies =====


@inject
def _get_intent_detection_service(
    svc: IntentDetectionService = Depends(Provide[Container.intent_detection_service]),
) -> IntentDetectionService:
    return svc


IntentDetectionServiceDep = Annotated[
    IntentDetectionService, Depends(_get_intent_detection_service)
]


@inject
def _get_intent_service(
    svc: IntentService = Depends(Provide[Container.intent_service]),
) -> IntentService:
    return svc


IntentServiceDep = Annotated[IntentService, Depends(_get_intent_service)]

__all__ = [
    "IntentDetectionServiceDep",
    "IntentServiceDep",
]
