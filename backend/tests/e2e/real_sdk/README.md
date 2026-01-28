# Real SDK Tests

This directory contains integration tests that use the **real Anthropic Claude API** instead of mocks. These tests are designed for manual validation and nightly CI runs, not for regular development workflows.

## Purpose

- **Validate end-to-end integration** with actual Claude API
- **Verify SSE streaming behavior** in production-like conditions
- **Test complex scenarios** that require real model responses
- **Ensure API contract compatibility** across SDK versions

## ⚠️ Important Notes

1. **API Credits**: These tests consume real Anthropic API credits
2. **Slower Execution**: Each test makes actual API calls (2-10 seconds per test)
3. **Network Required**: Tests will fail without internet connectivity
4. **Non-Deterministic**: Real model responses may vary between runs
5. **Not for CI**: These tests are excluded from default CI pipelines

## Running Tests

### Prerequisites

1. **Valid Anthropic API Key**:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

2. **Verify API Key**:
   ```bash
   # Ensure key is NOT a test key (sk-ant-test-...)
   echo $ANTHROPIC_API_KEY
   ```

### Run All Real SDK Tests

```bash
# From backend directory
cd /Users/tindang/workspaces/tind-repo/pilot-space/backend

# Run all real SDK tests
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/ -v
```

### Run Specific Test Files

```bash
# Chat flow tests only
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_chat_real.py -v

# Streaming tests only
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_streaming_real.py -v
```

### Run Specific Test Functions

```bash
# Single test
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_chat_real.py::test_real_chat_simple_query -v
```

## Excluding from CI

To run **only mock-based tests** (default CI behavior):

```bash
# Exclude real_sdk tests
uv run pytest -m "not real_sdk"
```

To run **only real SDK tests**:

```bash
# Include only real_sdk tests
ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m "real_sdk"
```

## Test Coverage

### Chat Flow Tests (`test_chat_real.py`)

| Test | Purpose |
|------|---------|
| `test_real_chat_simple_query` | Basic question-answer validation |
| `test_real_chat_multi_turn` | Session persistence and context retention |
| `test_real_chat_with_tools` | Tool usage and SSE event tracking |
| `test_real_chat_error_handling` | Error response validation |

### Streaming Tests (`test_streaming_real.py`)

| Test | Purpose |
|------|---------|
| `test_real_streaming_event_sequence` | SSE event ordering |
| `test_real_streaming_incremental_delivery` | Chunk-based streaming (not buffered) |
| `test_real_streaming_json_validity` | JSON escaping and formatting |
| `test_real_streaming_error_event_format` | Error event structure |
| `test_real_subagent_streaming` | Subagent delegation streaming |

## Expected Behavior

### When API Key is Missing

```
SKIPPED [1] tests/e2e/real_sdk/conftest.py:32: Real ANTHROPIC_API_KEY not configured
```

### When API Key is Test Key

```
SKIPPED [1] tests/e2e/real_sdk/conftest.py:35: Test API key detected, real API key required
```

### When Tests Pass

```
tests/e2e/real_sdk/test_chat_real.py::test_real_chat_simple_query PASSED [ 25%]
tests/e2e/real_sdk/test_chat_real.py::test_real_chat_multi_turn PASSED [ 50%]
tests/e2e/real_sdk/test_streaming_real.py::test_real_streaming_event_sequence PASSED [ 75%]
tests/e2e/real_sdk/test_streaming_real.py::test_real_streaming_incremental_delivery PASSED [100%]

====== 4 passed in 12.34s ======
```

## Nightly CI Configuration

For GitHub Actions nightly runs:

```yaml
# .github/workflows/nightly-real-sdk.yml
name: Nightly Real SDK Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  real-sdk-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          uv sync
      - name: Run real SDK tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd backend
          uv run pytest tests/e2e/real_sdk/ -v --maxfail=3
```

## Debugging Failed Tests

### Enable Verbose Logging

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/ -vv -s
```

### Capture API Responses

```bash
# Add print statements in test to see raw responses
ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_chat_real.py::test_real_chat_simple_query -vv -s
```

### Check API Key Validity

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Cost Estimation

**Per Test Run** (9 tests):
- **API Calls**: ~12-15 requests
- **Tokens**: ~5,000-10,000 tokens total
- **Cost**: ~$0.03-$0.08 USD (varies by model pricing)

**Nightly Runs** (30 days):
- **Monthly Cost**: ~$1-$2.50 USD

## Maintenance

### Updating Tests

When updating tests:
1. Ensure API key is **not** hardcoded
2. Use `real_api_key` fixture for key management
3. Mark new tests with `@pytest.mark.real_sdk`
4. Handle non-deterministic responses gracefully
5. Include clear assertions that work with varied responses

### Adding New Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_new_feature(real_sdk_client: AsyncClient) -> None:
    """Test new feature with real API."""
    # ... test implementation
```

## References

- **Plan**: `/Users/tindang/.claude/plans/peppy-whistling-swan.md` (Phase 6)
- **Mock Tests**: `tests/e2e/test_chat_flow.py`
- **Fixtures**: `tests/e2e/real_sdk/conftest.py`
- **Markers**: `pytest.ini` (real_sdk marker configuration)
