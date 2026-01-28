"""Real SDK integration tests.

Tests in this package use the actual Anthropic Claude API instead of mocks.
They are designed for manual validation and nightly CI runs.

Requires:
    - Valid ANTHROPIC_API_KEY environment variable
    - Internet connectivity
    - API credits

Usage:
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/ -v

See README.md for detailed usage instructions.
"""
