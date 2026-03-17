"""Tests for PilotSpaceAgent BYOK enforcement (AIGOV-05).

Phase 4 — AI Governance:
PilotSpaceAgent must enforce BYOK — workspace_id must have a configured
provider to use AI features. The _get_api_key method was replaced by the shared
resolve_workspace_llm_config helper in provider_selector.py.

See tests/unit/services/test_workspace_provider_resolution.py for current
workspace provider resolution tests.
"""
