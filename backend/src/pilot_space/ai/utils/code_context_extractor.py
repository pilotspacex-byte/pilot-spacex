"""Code context extraction utilities.

T204: Create CodeContextExtractor for analyzing code from GitHub.

Extracts relevant code context from:
- GitHub commits and pull requests
- File paths
- Code dependencies

Supports Python, TypeScript, and Go languages.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    UNKNOWN = "unknown"


@dataclass
class CodeReference:
    """A reference to code in a file.

    Attributes:
        file_path: Path to the file.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed).
        description: Description of the code.
        relevance: Relevance level (high, medium, low).
        source: Source of the reference (commit, pull_request, manual).
        source_id: External ID of the source.
        language: Programming language.
        snippet: Optional code snippet.
    """

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    description: str = ""
    relevance: str = "medium"
    source: str = "manual"
    source_id: str | None = None
    language: Language = Language.UNKNOWN
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "description": self.description,
            "relevance": self.relevance,
            "source": self.source,
            "source_id": self.source_id,
            "language": self.language.value,
            "snippet": self.snippet,
        }


@dataclass
class ExtractedDependency:
    """An extracted dependency from code.

    Attributes:
        name: Dependency name.
        version: Version constraint if known.
        source_file: File where dependency was found.
        import_statement: The import statement.
    """

    name: str
    version: str | None = None
    source_file: str | None = None
    import_statement: str | None = None


@dataclass
class CodeAnalysisResult:
    """Result of code analysis.

    Attributes:
        references: List of code references.
        dependencies: List of dependencies.
        entry_points: Main entry point files.
        test_files: Related test files.
        affected_modules: Affected modules/packages.
    """

    references: list[CodeReference] = field(default_factory=list)
    dependencies: list[ExtractedDependency] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)


class CodeContextExtractor:
    """Extracts code context from various sources.

    Provides methods to:
    - Extract references from GitHub commits/PRs
    - Analyze file paths and dependencies
    - Detect programming languages
    """

    # File extension to language mapping
    EXTENSION_MAP: ClassVar[dict[str, Language]] = {
        ".py": Language.PYTHON,
        ".pyi": Language.PYTHON,
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".js": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".mjs": Language.JAVASCRIPT,
        ".go": Language.GO,
    }

    # Patterns for extracting imports
    IMPORT_PATTERNS: ClassVar[dict[Language, list[re.Pattern[str]]]] = {
        Language.PYTHON: [
            re.compile(r"^import\s+(\w+(?:\.\w+)*)", re.MULTILINE),
            re.compile(r"^from\s+(\w+(?:\.\w+)*)\s+import", re.MULTILINE),
        ],
        Language.TYPESCRIPT: [
            re.compile(r"^import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            re.compile(r"^import\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        ],
        Language.JAVASCRIPT: [
            re.compile(r"^import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            re.compile(r"^const\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE),
        ],
        Language.GO: [
            re.compile(r"^import\s+\"([^\"]+)\"", re.MULTILINE),
            re.compile(r"^\t\"([^\"]+)\"", re.MULTILINE),  # Grouped imports
        ],
    }

    # Test file patterns
    TEST_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"test_.*\.py$"),
        re.compile(r".*_test\.py$"),
        re.compile(r".*\.test\.[jt]sx?$"),
        re.compile(r".*\.spec\.[jt]sx?$"),
        re.compile(r"__tests__/.*\.[jt]sx?$"),
        re.compile(r".*_test\.go$"),
    ]

    def detect_language(self, file_path: str) -> Language:
        """Detect programming language from file path.

        Args:
            file_path: Path to the file.

        Returns:
            Detected language.
        """
        for ext, lang in self.EXTENSION_MAP.items():
            if file_path.endswith(ext):
                return lang
        return Language.UNKNOWN

    def is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file.

        Args:
            file_path: Path to the file.

        Returns:
            True if test file, False otherwise.
        """
        return any(pattern.search(file_path) for pattern in self.TEST_PATTERNS)

    def extract_from_github_commit(
        self,
        commit_data: dict[str, Any],
        integration_id: str,
    ) -> list[CodeReference]:
        """Extract code references from a GitHub commit.

        Args:
            commit_data: GitHub commit API response.
            integration_id: Integration ID for source tracking.

        Returns:
            List of code references.
        """
        references: list[CodeReference] = []

        files = commit_data.get("files", [])
        commit_sha = commit_data.get("sha", "")
        commit_message = commit_data.get("commit", {}).get("message", "")

        for file_data in files:
            file_path = file_data.get("filename", "")
            if not file_path:
                continue

            language = self.detect_language(file_path)
            status = file_data.get("status", "modified")
            additions = file_data.get("additions", 0)
            deletions = file_data.get("deletions", 0)

            # Calculate relevance based on changes
            total_changes = additions + deletions
            relevance = "high" if total_changes > 50 else "medium" if total_changes > 10 else "low"

            description = f"{status.capitalize()}: +{additions}/-{deletions} lines"
            if commit_message:
                # Add first line of commit message
                first_line = commit_message.split("\n")[0][:100]
                description = f"{first_line} ({description})"

            reference = CodeReference(
                file_path=file_path,
                description=description,
                relevance=relevance,
                source="commit",
                source_id=commit_sha,
                language=language,
            )

            # Try to extract line range from patch
            patch = file_data.get("patch", "")
            if patch:
                line_range = self._extract_line_range_from_patch(patch)
                if line_range:
                    reference.line_start, reference.line_end = line_range

            references.append(reference)

        return references

    def extract_from_github_pr(
        self,
        pr_data: dict[str, Any],
        pr_files: list[dict[str, Any]],
        integration_id: str,
    ) -> list[CodeReference]:
        """Extract code references from a GitHub pull request.

        Args:
            pr_data: GitHub PR API response.
            pr_files: List of files in the PR.
            integration_id: Integration ID for source tracking.

        Returns:
            List of code references.
        """
        references: list[CodeReference] = []

        pr_number = pr_data.get("number", 0)

        for file_data in pr_files:
            file_path = file_data.get("filename", "")
            if not file_path:
                continue

            language = self.detect_language(file_path)
            status = file_data.get("status", "modified")
            additions = file_data.get("additions", 0)
            deletions = file_data.get("deletions", 0)

            # Calculate relevance
            total_changes = additions + deletions
            relevance = "high" if total_changes > 100 else "medium" if total_changes > 20 else "low"

            description = f"PR #{pr_number}: {status} (+{additions}/-{deletions})"

            reference = CodeReference(
                file_path=file_path,
                description=description,
                relevance=relevance,
                source="pull_request",
                source_id=str(pr_number),
                language=language,
            )

            # Try to extract line range from patch
            patch = file_data.get("patch", "")
            if patch:
                line_range = self._extract_line_range_from_patch(patch)
                if line_range:
                    reference.line_start, reference.line_end = line_range

            references.append(reference)

        return references

    def extract_from_file_paths(
        self,
        file_paths: list[str],
        source: str = "manual",
    ) -> list[CodeReference]:
        """Create code references from file paths.

        Args:
            file_paths: List of file paths.
            source: Source identifier.

        Returns:
            List of code references.
        """
        references: list[CodeReference] = []

        for file_path in file_paths:
            language = self.detect_language(file_path)
            is_test = self.is_test_file(file_path)

            description = "Test file" if is_test else "Source file"
            relevance = "low" if is_test else "medium"

            references.append(
                CodeReference(
                    file_path=file_path,
                    description=description,
                    relevance=relevance,
                    source=source,
                    language=language,
                )
            )

        return references

    def analyze_dependencies(
        self,
        code_content: str,
        language: Language,
        file_path: str | None = None,
    ) -> list[ExtractedDependency]:
        """Extract dependencies from code content.

        Args:
            code_content: Source code content.
            language: Programming language.
            file_path: Optional source file path.

        Returns:
            List of extracted dependencies.
        """
        dependencies: list[ExtractedDependency] = []
        patterns = self.IMPORT_PATTERNS.get(language, [])

        for pattern in patterns:
            matches = pattern.findall(code_content)
            for match in matches:
                # Filter out relative imports
                if match.startswith("."):
                    continue

                dependencies.append(
                    ExtractedDependency(
                        name=match,
                        source_file=file_path,
                        import_statement=match,
                    )
                )

        return dependencies

    def analyze_codebase_structure(
        self,
        file_paths: list[str],
    ) -> CodeAnalysisResult:
        """Analyze codebase structure from file paths.

        Args:
            file_paths: List of file paths to analyze.

        Returns:
            CodeAnalysisResult with analysis.
        """
        result = CodeAnalysisResult()

        for file_path in file_paths:
            language = self.detect_language(file_path)

            # Create reference
            reference = CodeReference(
                file_path=file_path,
                language=language,
                relevance="medium",
            )
            result.references.append(reference)

            # Check if test file
            if self.is_test_file(file_path):
                result.test_files.append(file_path)

            # Extract module/package
            module = self._extract_module_name(file_path, language)
            if module and module not in result.affected_modules:
                result.affected_modules.append(module)

            # Check for entry points
            if self._is_entry_point(file_path, language):
                result.entry_points.append(file_path)

        return result

    def _extract_line_range_from_patch(
        self,
        patch: str,
    ) -> tuple[int, int] | None:
        """Extract line range from git patch.

        Args:
            patch: Git diff patch content.

        Returns:
            Tuple of (start_line, end_line) or None.
        """
        # Match @@ -old_start,old_count +new_start,new_count @@
        match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch)
        if match:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) else 1
            return start, start + count - 1
        return None

    def _extract_module_name(
        self,
        file_path: str,
        language: Language,
    ) -> str | None:
        """Extract module/package name from file path.

        Args:
            file_path: Path to file.
            language: Programming language.

        Returns:
            Module name or None.
        """
        if language == Language.PYTHON:
            # Extract Python package
            parts = file_path.replace("/", ".").split(".")
            if len(parts) >= 2:
                return parts[0]

        elif language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
            # Extract from path
            if "/" in file_path:
                parts = file_path.split("/")
                if "src" in parts:
                    idx = parts.index("src")
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
                return parts[0]

        elif language == Language.GO:
            # Extract Go package
            if "/" in file_path:
                parts = file_path.split("/")
                return parts[0] if parts else None

        return None

    def _is_entry_point(
        self,
        file_path: str,
        language: Language,
    ) -> bool:
        """Check if file is an entry point.

        Args:
            file_path: Path to file.
            language: Programming language.

        Returns:
            True if entry point, False otherwise.
        """
        entry_point_patterns: dict[Language, list[str]] = {
            Language.PYTHON: ["main.py", "__main__.py", "app.py", "cli.py"],
            Language.TYPESCRIPT: ["index.ts", "main.ts", "app.ts"],
            Language.JAVASCRIPT: ["index.js", "main.js", "app.js"],
            Language.GO: ["main.go", "cmd/"],
        }

        patterns = entry_point_patterns.get(language, [])
        file_name = file_path.split("/")[-1] if "/" in file_path else file_path

        return any(file_name == pattern or pattern in file_path for pattern in patterns)


# Singleton instance for convenience
_extractor: CodeContextExtractor | None = None


def get_code_extractor() -> CodeContextExtractor:
    """Get singleton CodeContextExtractor instance.

    Returns:
        CodeContextExtractor instance.
    """
    global _extractor  # noqa: PLW0603
    if _extractor is None:
        _extractor = CodeContextExtractor()
    return _extractor


__all__ = [
    "CodeAnalysisResult",
    "CodeContextExtractor",
    "CodeReference",
    "ExtractedDependency",
    "Language",
    "get_code_extractor",
]
