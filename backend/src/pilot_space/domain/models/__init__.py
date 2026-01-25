"""Domain models for Pilot Space.

Core entities:
- User: Platform user (synced with Supabase Auth)
- Workspace: Organization container
- Project: Issue/note container within workspace
- Issue: Work item with state machine and AI metadata
- Note: Block-based document with annotations
- Cycle: Sprint/iteration container
- Module: Epic-level grouping
"""
