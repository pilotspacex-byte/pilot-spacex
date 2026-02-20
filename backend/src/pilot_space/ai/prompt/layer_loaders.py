"""File I/O loaders for prompt template layers and rule files.

Provides cached loading of:
- Static prompt layer templates (templates/prompt_layers/*.md)
- Role-specific templates (templates/role_templates/*.md)
- Operational rule files (templates/rules/*.md)

All loaders use module-level caches with ``asyncio.Lock`` to prevent
redundant file reads under concurrent requests.
Call ``clear_caches()`` in tests to reset state between runs.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"
_PROMPT_LAYERS_DIR: Path = _TEMPLATES_DIR / "prompt_layers"
_ROLE_TEMPLATES_DIR: Path = _TEMPLATES_DIR / "role_templates"
_RULES_DIR: Path = _TEMPLATES_DIR / "rules"

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

_MAX_RULE_CHARS: int = 4000

# ---------------------------------------------------------------------------
# Module-level caches (guarded by asyncio.Lock)
# ---------------------------------------------------------------------------

_template_cache: dict[str, str] = {}
_rule_cache: dict[str, str] = {}
_template_lock = asyncio.Lock()
_rule_lock = asyncio.Lock()


async def load_static_layer(filename: str) -> str:
    """Load a static prompt layer template from ``templates/prompt_layers/``.

    Results are cached after the first read. Lock prevents redundant
    file reads when multiple requests hit a cold cache concurrently.

    Args:
        filename: Template filename (e.g. ``layer1_identity.md``).

    Returns:
        Template content, or empty string if the file does not exist.
    """
    cache_key = f"layer:{filename}"
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    async with _template_lock:
        # Double-check after acquiring lock
        if cache_key in _template_cache:
            return _template_cache[cache_key]

        filepath = _PROMPT_LAYERS_DIR / filename
        if not filepath.is_file():
            logger.debug("Prompt layer template not found: %s", filepath)
            return ""

        content = await asyncio.to_thread(filepath.read_text, encoding="utf-8")
        _template_cache[cache_key] = content
        return content


async def load_role_template(role_type: str) -> str | None:
    """Load a role template, stripping YAML frontmatter.

    Results are cached after the first read. Lock prevents redundant
    file reads when multiple requests hit a cold cache concurrently.

    Args:
        role_type: Role type string (e.g. ``developer``, ``architect``).

    Returns:
        Template body (frontmatter removed), or ``None`` if not found.
    """
    cache_key = f"role:{role_type}"
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    async with _template_lock:
        if cache_key in _template_cache:
            return _template_cache[cache_key]

        template_path = _ROLE_TEMPLATES_DIR / f"{role_type}.md"
        if not template_path.is_file():
            logger.debug("Role template not found: %s", template_path)
            return None

        content = await asyncio.to_thread(template_path.read_text, encoding="utf-8")

        # Strip YAML frontmatter (--- ... ---)
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3 :].strip()

        _template_cache[cache_key] = content
        return content


async def load_rule_file(filename: str) -> str:
    """Load a rule file from ``templates/rules/``, truncating at 4000 chars.

    Results are cached after the first read. Lock prevents redundant
    file reads when multiple requests hit a cold cache concurrently.

    Args:
        filename: Rule filename (e.g. ``issues.md``).

    Returns:
        Rule content (possibly truncated), or empty string if not found.
    """
    if filename in _rule_cache:
        return _rule_cache[filename]

    async with _rule_lock:
        if filename in _rule_cache:
            return _rule_cache[filename]

        rule_path = _RULES_DIR / filename
        if not rule_path.is_file():
            logger.debug("Rule file not found: %s", rule_path)
            return ""

        content = await asyncio.to_thread(rule_path.read_text, encoding="utf-8")
        if len(content) > _MAX_RULE_CHARS:
            content = content[:_MAX_RULE_CHARS] + "\n... (truncated)"

        _rule_cache[filename] = content
        return content


def clear_caches() -> None:
    """Clear all module-level caches. Call in tests to reset state."""
    _template_cache.clear()
    _rule_cache.clear()
