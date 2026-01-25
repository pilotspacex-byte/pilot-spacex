"""Pilot Space - AI-Augmented SDLC Platform with Note-First Workflow.

This package provides the backend API for Pilot Space, including:
- RESTful API endpoints for workspace, project, and issue management
- AI agents for ghost text, PR review, and context generation
- Integration with GitHub and Slack
- Infrastructure for database, cache, queue, and search

Architecture: Clean Architecture with CQRS-lite pattern
- api/: Presentation layer (FastAPI routers, schemas, middleware)
- domain/: Business domain (models, services, events)
- application/: Application services (command/query handlers)
- infrastructure/: External systems (database, cache, queue, search)
- ai/: AI layer (agents, prompts, RAG pipeline)
- integrations/: Third-party integrations (GitHub, Slack)
"""

__version__ = "0.1.0"
