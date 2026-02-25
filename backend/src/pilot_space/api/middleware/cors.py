"""CORS middleware configuration.

Configures Cross-Origin Resource Sharing for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pilot_space.config import Settings, get_settings


def configure_cors(app: FastAPI, settings: Settings | None = None) -> None:
    """Configure CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance.
        settings: Application settings. If None, loads from environment.
    """
    if settings is None:
        settings = get_settings()

    origins = settings.cors_origins
    # Wildcard "*" is incompatible with allow_credentials=True (browsers reject it).
    # Use allow_origin_regex to reflect the actual Origin header instead.
    if origins == ["*"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_origin_regex=r".*",
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Accept-Language",
                "Authorization",
                "Content-Language",
                "Content-Type",
                "X-Request-ID",
                "X-Workspace-ID",
            ],
            expose_headers=[
                "X-Request-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After",
            ],
            max_age=600,
        )
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Authorization",
            "Content-Language",
            "Content-Type",
            "X-Request-ID",
            "X-Workspace-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
        max_age=600,  # Cache preflight for 10 minutes
    )


__all__ = ["configure_cors"]
