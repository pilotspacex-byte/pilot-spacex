"""Application layer for Pilot Space.

This package contains application services following CQRS-lite pattern:
- services/: Command and query handlers

Pattern: Service Classes with Payloads
- CreateIssueService.execute(payload) -> Issue
- GetIssueService.execute(issue_id) -> Issue
"""
