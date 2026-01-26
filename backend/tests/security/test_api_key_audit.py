"""T324: Audit API Key Handling

Automated tests to verify API keys are never logged or leaked.
Complements manual bash audit from task specification.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest


class CodeSecurityAuditor:
    """Auditor for code security issues related to API key handling."""

    def __init__(self, base_path: Path) -> None:
        """Initialize auditor.

        Args:
            base_path: Base path to scan for Python files.
        """
        self.base_path = base_path
        self.issues: list[dict[str, Any]] = []

    def scan_for_key_logging(self) -> list[dict[str, Any]]:
        """Scan for potential API key logging.

        Returns:
            List of issues found.
        """
        python_files = list(self.base_path.rglob("*.py"))

        for file_path in python_files:
            # Skip test files and __pycache__
            if "__pycache__" in str(file_path) or "tests/" in str(file_path):
                continue

            try:
                content = file_path.read_text()
                self._check_file_for_key_logging(file_path, content)
            except Exception:
                # Skip files that can't be read
                continue

        return self.issues

    def _check_file_for_key_logging(self, file_path: Path, content: str) -> None:
        """Check a single file for key logging issues.

        Args:
            file_path: Path to the file.
            content: File contents.
        """
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Check for log statements with "api_key" or "key" in same line
            if self._is_potential_key_logging(line):
                self.issues.append(
                    {
                        "file": str(file_path.relative_to(self.base_path)),
                        "line": line_num,
                        "code": line.strip(),
                        "severity": "high",
                        "message": "Potential API key logging detected",
                    }
                )

            # Check for print statements with key variables
            if self._is_print_with_key(line):
                self.issues.append(
                    {
                        "file": str(file_path.relative_to(self.base_path)),
                        "line": line_num,
                        "code": line.strip(),
                        "severity": "high",
                        "message": "Print statement with potential key variable",
                    }
                )

            # Check for exception messages that might leak keys
            if self._is_exception_with_key(line):
                self.issues.append(
                    {
                        "file": str(file_path.relative_to(self.base_path)),
                        "line": line_num,
                        "code": line.strip(),
                        "severity": "medium",
                        "message": "Exception might expose key in message",
                    }
                )

    def _is_potential_key_logging(self, line: str) -> bool:
        """Check if line potentially logs an API key.

        Args:
            line: Code line to check.

        Returns:
            True if suspicious.
        """
        # Skip comments
        if line.strip().startswith("#"):
            return False

        # Check for logging with key variables (excluding encrypted)
        log_patterns = [
            r"log.*api_key(?!.*encrypt)",
            r"logger.*api_key(?!.*encrypt)",
            r"log.*\.key(?!.*encrypt)",
            r"logging.*api_key(?!.*encrypt)",
        ]

        return any(re.search(pattern, line, re.IGNORECASE) for pattern in log_patterns)

    def _is_print_with_key(self, line: str) -> bool:
        """Check if line prints a key variable.

        Args:
            line: Code line to check.

        Returns:
            True if suspicious.
        """
        if "print(" not in line:
            return False

        key_indicators = ["api_key", "_key", "secret", "token"]

        for indicator in key_indicators:
            if indicator in line.lower():
                # Allow if it's clearly a placeholder or label
                if "encrypted" in line.lower() or indicator + ":" in line:
                    continue
                return True

        return False

    def _is_exception_with_key(self, line: str) -> bool:
        """Check if exception message might expose key.

        Args:
            line: Code line to check.

        Returns:
            True if suspicious.
        """
        if not any(word in line for word in ["raise", "Exception", "Error"]):
            return False

        # Check if exception message includes key variable without masking
        if "api_key" in line.lower() or "token" in line.lower():
            # Allow if it's just mentioning the field name
            return 'api_key":' not in line and "api_key}" in line

        return False


class TestAPIKeySecurityAudit:
    """Automated tests for API key security."""

    def test_no_api_keys_logged(self, ai_source_path: Path) -> None:
        """Verify API keys are never logged in code.

        This test scans all Python files in the AI module for patterns
        that might log API keys.
        """
        auditor = CodeSecurityAuditor(ai_source_path)
        issues = auditor.scan_for_key_logging()

        # Filter out false positives (if any)
        real_issues = [
            issue
            for issue in issues
            if "# Safe" not in issue["code"]  # Allow explicitly marked safe lines
        ]

        if real_issues:
            error_msg = "API key logging detected:\n"
            for issue in real_issues:
                error_msg += (
                    f"  {issue['file']}:{issue['line']} "
                    f"({issue['severity']}): {issue['message']}\n"
                    f"    {issue['code']}\n"
                )

            pytest.fail(error_msg)

    def test_key_storage_uses_vault(self, ai_source_path: Path) -> None:
        """Verify API keys are stored using Supabase Vault."""
        # Check that key_storage.py uses proper encryption
        key_storage_file = ai_source_path / "infrastructure" / "key_storage.py"

        if not key_storage_file.exists():
            pytest.skip("key_storage.py not found")

        content = key_storage_file.read_text()

        # Should use Supabase Vault or encryption
        assert "vault" in content.lower() or "encrypt" in content.lower(), (
            "API key storage must use Supabase Vault or encryption"
        )

        # Should not store keys in plain text
        assert "api_key = " not in content or "encrypted" in content, (
            "API keys must not be stored in plain text"
        )

    def test_no_hardcoded_api_keys(self, ai_source_path: Path) -> None:
        """Verify no hardcoded API keys in source code."""
        # Pattern for potential API keys (anthropic, openai, etc.)
        key_patterns = [
            r"sk-[a-zA-Z0-9]{40,}",  # OpenAI-style keys
            r"sk-ant-[a-zA-Z0-9]{40,}",  # Anthropic keys
            r"AIza[a-zA-Z0-9_-]{35}",  # Google API keys
        ]

        python_files = list(ai_source_path.rglob("*.py"))
        violations = []

        for file_path in python_files:
            if "__pycache__" in str(file_path) or "tests/" in str(file_path):
                continue

            try:
                content = file_path.read_text()

                for pattern in key_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        violations.append(
                            {
                                "file": str(file_path.relative_to(ai_source_path)),
                                "pattern": pattern,
                                "match": match.group(),
                            }
                        )
            except Exception:
                continue

        if violations:
            error_msg = "Hardcoded API keys detected:\n"
            for v in violations:
                error_msg += f"  {v['file']}: {v['match'][:20]}...\n"
            pytest.fail(error_msg)

    def test_error_messages_do_not_leak_keys(self, ai_source_path: Path) -> None:
        """Verify error messages don't include full API keys."""
        python_files = list(ai_source_path.rglob("*.py"))
        violations = []

        for file_path in python_files:
            if "__pycache__" in str(file_path) or "tests/" in str(file_path):
                continue

            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Raise):
                        # Check exception messages
                        if isinstance(node.exc, ast.Call):
                            for arg in node.exc.args:
                                if isinstance(arg, ast.JoinedStr):
                                    # f-string - check for key variables
                                    for value in arg.values:
                                        if isinstance(value, ast.FormattedValue):
                                            if isinstance(value.value, ast.Name):
                                                if "key" in value.value.id.lower():
                                                    violations.append(
                                                        {
                                                            "file": str(
                                                                file_path.relative_to(
                                                                    ai_source_path
                                                                )
                                                            ),
                                                            "line": node.lineno,
                                                            "message": "Exception includes key variable",
                                                        }
                                                    )
            except Exception:
                # Skip files that can't be parsed
                continue

        # Allow if keys are explicitly masked
        real_violations = [v for v in violations if "mask" not in str(v).lower()]

        if real_violations:
            error_msg = "Error messages may leak API keys:\n"
            for v in real_violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['message']}\n"
            pytest.fail(error_msg)


@pytest.fixture
def ai_source_path() -> Path:
    """Get path to AI source code."""
    # Assuming tests are in backend/tests/security
    current = Path(__file__).parent
    return current.parent.parent / "src" / "pilot_space" / "ai"
