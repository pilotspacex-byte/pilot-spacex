"""PR Review MCP tool for reviewing pull requests.

Integrates with GitHub API to fetch PR data and provide structured review feedback.

Reference: T084-T088 (PR Review MCP Integration)
Design Decisions: DD-011 (Claude for code review)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from pilot_space.ai.mcp.base import (
    MCPTool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
)

logger = logging.getLogger(__name__)


class PRReviewResult(BaseModel):
    """Structured PR review result.

    Attributes:
        summary: Overall summary of the review.
        architecture: Architecture-level findings.
        code_quality: Code quality issues.
        security: Security concerns.
        performance: Performance considerations.
        documentation: Documentation gaps.
        recommendations: Actionable recommendations.
        approval_status: Recommended approval status.
    """

    summary: str = Field(..., description="Overall review summary")
    architecture: list[str] = Field(
        default_factory=list,
        description="Architecture-level findings",
    )
    code_quality: list[str] = Field(
        default_factory=list,
        description="Code quality issues",
    )
    security: list[str] = Field(
        default_factory=list,
        description="Security concerns",
    )
    performance: list[str] = Field(
        default_factory=list,
        description="Performance considerations",
    )
    documentation: list[str] = Field(
        default_factory=list,
        description="Documentation gaps",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations",
    )
    approval_status: str = Field(
        ...,
        description="Recommended approval status (approve, comment, request_changes)",
    )


class PRReviewTool(MCPTool):
    """MCP tool for reviewing GitHub pull requests.

    Fetches PR data via GitHub API and provides structured review feedback
    covering architecture, code quality, security, performance, and documentation.

    Example usage:
        tool = PRReviewTool(github_client)
        result = await tool.execute(
            workspace_id=workspace_id,
            user_id=user_id,
            repo="owner/repo",
            pr_number=123,
            review_type="full",
        )
    """

    def __init__(self, github_client: Any) -> None:
        """Initialize PR review tool.

        Args:
            github_client: GitHubClient for API access.
        """
        self._github_client = github_client

    @property
    def name(self) -> str:
        """Tool name."""
        return "review_pull_request"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Review a GitHub pull request with architecture, code quality, "
            "security, performance, and documentation analysis"
        )

    @property
    def parameters(self) -> list[ToolParameter]:
        """Tool parameters."""
        return [
            ToolParameter(
                name="repo",
                type=ToolParameterType.STRING,
                description="Repository name (owner/repo format)",
                required=True,
            ),
            ToolParameter(
                name="pr_number",
                type=ToolParameterType.INTEGER,
                description="Pull request number",
                required=True,
            ),
            ToolParameter(
                name="review_type",
                type=ToolParameterType.STRING,
                description="Type of review to perform",
                required=False,
                default="full",
                enum=["full", "quick", "security_only"],
            ),
        ]

    @property
    def requires_approval(self) -> bool:
        """PR review is read-only, no approval needed."""
        return False

    async def execute(
        self,
        workspace_id: UUID,
        user_id: UUID,
        **params: Any,
    ) -> ToolResult:
        """Execute PR review.

        Args:
            workspace_id: Workspace UUID for RLS.
            user_id: User UUID for attribution.
            **params: Tool parameters (repo, pr_number, review_type).

        Returns:
            ToolResult with structured review feedback.
        """
        repo = params.get("repo")
        pr_number = params.get("pr_number")
        review_type = params.get("review_type", "full")

        if not repo or not pr_number:
            return ToolResult.fail("Missing required parameters: repo, pr_number")

        try:
            # Parse repo owner/name
            parts = repo.split("/")
            if len(parts) != 2:
                return ToolResult.fail("Invalid repo format. Use: owner/repo")

            owner, repo_name = parts

            # Fetch PR data from GitHub
            pr_data = await self._fetch_pr_data(owner, repo_name, pr_number)

            # Perform review based on type
            if review_type == "quick":
                review_result = await self._quick_review(pr_data)
            elif review_type == "security_only":
                review_result = await self._security_review(pr_data)
            else:  # full
                review_result = await self._full_review(pr_data)

            logger.info(
                "Completed PR review",
                extra={
                    "workspace_id": str(workspace_id),
                    "user_id": str(user_id),
                    "repo": repo,
                    "pr_number": pr_number,
                    "review_type": review_type,
                },
            )

            return ToolResult.ok(
                data=review_result.model_dump(),
                metadata={
                    "repo": repo,
                    "pr_number": pr_number,
                    "review_type": review_type,
                },
            )

        except Exception as e:
            logger.exception("PR review failed")
            return ToolResult.fail(
                error=f"Failed to review PR: {e!s}",
                metadata={"repo": repo, "pr_number": pr_number},
            )

    async def _fetch_pr_data(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict[str, Any]:
        """Fetch PR data from GitHub API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.

        Returns:
            PR data dictionary.
        """
        from pilot_space.integrations.github import GitHubClient

        client: GitHubClient = self._github_client

        # Fetch PR details
        pr = await client.get_pull_request(owner, repo, pr_number)

        # Fetch PR diff (method may not be in type stubs)
        diff = await client.get_pull_request_diff(owner, repo, pr_number)  # type: ignore[attr-defined]

        # Fetch PR files (method may not be in type stubs)
        files = await client.get_pull_request_files(owner, repo, pr_number)  # type: ignore[attr-defined]

        return {
            "pr": pr,
            "diff": diff,
            "files": files,
        }

    async def _full_review(self, pr_data: dict[str, Any]) -> PRReviewResult:
        """Perform full PR review.

        Args:
            pr_data: PR data from GitHub.

        Returns:
            Structured review result.
        """
        # Extract data
        pr = pr_data["pr"]
        files = pr_data.get("files", [])

        # Analyze architecture
        architecture_findings = self._analyze_architecture(files)

        # Analyze code quality
        code_quality_findings = self._analyze_code_quality(files)

        # Analyze security
        security_findings = self._analyze_security(files)

        # Analyze performance
        performance_findings = self._analyze_performance(files)

        # Check documentation
        doc_findings = self._check_documentation(pr, files)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            architecture_findings,
            code_quality_findings,
            security_findings,
            performance_findings,
            doc_findings,
        )

        # Determine approval status
        approval_status = self._determine_approval_status(
            security_findings,
            code_quality_findings,
        )

        return PRReviewResult(
            summary=f"Reviewed PR #{pr.number}: {pr.title}",
            architecture=architecture_findings,
            code_quality=code_quality_findings,
            security=security_findings,
            performance=performance_findings,
            documentation=doc_findings,
            recommendations=recommendations,
            approval_status=approval_status,
        )

    async def _quick_review(self, pr_data: dict[str, Any]) -> PRReviewResult:
        """Perform quick PR review (code quality + security only).

        Args:
            pr_data: PR data from GitHub.

        Returns:
            Quick review result.
        """
        pr = pr_data["pr"]
        files = pr_data.get("files", [])

        code_quality_findings = self._analyze_code_quality(files)
        security_findings = self._analyze_security(files)

        return PRReviewResult(
            summary=f"Quick review of PR #{pr.number}",
            code_quality=code_quality_findings,
            security=security_findings,
            recommendations=["Consider full review for production changes"],
            approval_status=self._determine_approval_status(
                security_findings, code_quality_findings
            ),
        )

    async def _security_review(self, pr_data: dict[str, Any]) -> PRReviewResult:
        """Perform security-focused PR review.

        Args:
            pr_data: PR data from GitHub.

        Returns:
            Security review result.
        """
        pr = pr_data["pr"]
        files = pr_data.get("files", [])

        security_findings = self._analyze_security(files)

        return PRReviewResult(
            summary=f"Security review of PR #{pr.number}",
            security=security_findings,
            recommendations=self._generate_security_recommendations(security_findings),
            approval_status="request_changes" if security_findings else "approve",
        )

    def _analyze_architecture(self, files: list[Any]) -> list[str]:
        """Analyze architecture patterns (placeholder).

        Args:
            files: List of changed files.

        Returns:
            List of architecture findings.
        """
        findings = []

        # Check for large files (>500 lines changed)
        large_files = [f for f in files if f.changes > 500]
        if large_files:
            findings.append(
                f"Large changes detected in {len(large_files)} files. Consider breaking into smaller PRs."
            )

        return findings

    def _analyze_code_quality(self, files: list[Any]) -> list[str]:
        """Analyze code quality (placeholder).

        Args:
            files: List of changed files.

        Returns:
            List of code quality findings.
        """
        findings = []

        # Check for test coverage
        test_files = [f for f in files if "test" in f.filename.lower()]
        if len(files) > 3 and not test_files:
            findings.append("No test files found. Consider adding tests for new functionality.")

        return findings

    def _analyze_security(self, files: list[Any]) -> list[str]:
        """Analyze security concerns (placeholder).

        Args:
            files: List of changed files.

        Returns:
            List of security findings.
        """
        findings = []

        # Check for sensitive file patterns
        sensitive_patterns = [".env", "secret", "password", "token", "key"]
        for file in files:
            if any(pattern in file.filename.lower() for pattern in sensitive_patterns):
                findings.append(
                    f"Sensitive file detected: {file.filename}. Verify no secrets committed."
                )

        return findings

    def _analyze_performance(self, files: list[Any]) -> list[str]:
        """Analyze performance considerations (placeholder).

        Args:
            files: List of changed files.

        Returns:
            List of performance findings.
        """
        _ = files  # Reserved for future performance analysis
        return []

    def _check_documentation(self, pr: Any, files: list[Any]) -> list[str]:
        """Check documentation (placeholder).

        Args:
            pr: PR object.
            files: List of changed files.

        Returns:
            List of documentation findings.
        """
        _ = files  # Reserved for future file-based doc checks
        findings = []

        # Check for missing PR description
        if not pr.body or len(pr.body) < 50:
            findings.append("PR description is too short. Add context and testing notes.")

        return findings

    def _generate_recommendations(self, *findings_lists: list[str]) -> list[str]:
        """Generate actionable recommendations.

        Args:
            *findings_lists: Variable number of findings lists.

        Returns:
            List of recommendations.
        """
        recommendations = []

        total_findings = sum(len(findings) for findings in findings_lists)

        if total_findings == 0:
            recommendations.append("No major issues found. Looks good to merge!")
        elif total_findings < 3:
            recommendations.append("Address minor issues before merging.")
        else:
            recommendations.append(
                "Consider addressing findings before merge or scheduling follow-up work."
            )

        return recommendations

    def _generate_security_recommendations(self, security_findings: list[str]) -> list[str]:
        """Generate security-specific recommendations.

        Args:
            security_findings: List of security findings.

        Returns:
            List of security recommendations.
        """
        if not security_findings:
            return ["No security concerns identified."]

        return [
            "Review security findings carefully.",
            "Consider security team review for sensitive changes.",
        ]

    def _determine_approval_status(
        self,
        security_findings: list[str],
        code_quality_findings: list[str],
    ) -> str:
        """Determine recommended approval status.

        Args:
            security_findings: List of security findings.
            code_quality_findings: List of code quality findings.

        Returns:
            Approval status (approve, comment, request_changes).
        """
        if security_findings:
            return "request_changes"

        if len(code_quality_findings) > 5:
            return "request_changes"

        if code_quality_findings:
            return "comment"

        return "approve"


__all__ = ["PRReviewResult", "PRReviewTool"]
