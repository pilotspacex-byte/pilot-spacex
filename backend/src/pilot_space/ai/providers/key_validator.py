"""AI Provider Key Validator.

Validates API keys with provider APIs.

T028: Create AIProviderKeyValidator.
Source: FR-005, FR-006, US2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

import httpx


@dataclass
class KeyValidationResult:
    """Result of API key validation.

    Attributes:
        valid: Whether the key is valid.
        error_message: Human-readable error if invalid.
        models_available: List of models available with this key.
    """

    valid: bool
    error_message: str | None = None
    models_available: list[str] = field(default_factory=list)


class AIProviderKeyValidator:
    """Validates AI provider API keys.

    Makes lightweight authenticated requests to verify key validity.
    Uses 10s timeout per plan specification.
    """

    ANTHROPIC_API_BASE = "https://api.anthropic.com"
    TIMEOUT_SECONDS = 10

    # HTTP status code to error message mapping
    _ERROR_MESSAGES: ClassVar[dict[int, str]] = {
        401: "Authentication failed — check your key at console.anthropic.com",
        403: "Insufficient permissions for this API key",
        429: "Rate limited — try again in a few minutes",
    }

    async def validate_anthropic_key(self, api_key: str) -> KeyValidationResult:
        """Validate Anthropic API key.

        Makes GET request to /v1/models to verify key authentication.

        Args:
            api_key: Anthropic API key to validate.

        Returns:
            KeyValidationResult with validation status.
        """
        # Early validation
        validation_error = self._validate_key_format(api_key)
        if validation_error:
            return validation_error

        # Make API request
        return await self._call_anthropic_api(api_key)

    def _validate_key_format(self, api_key: str) -> KeyValidationResult | None:
        """Validate API key format before making request.

        Args:
            api_key: Anthropic API key to validate.

        Returns:
            KeyValidationResult if validation fails, None if format is valid.
        """
        if not api_key or not api_key.strip():
            return KeyValidationResult(
                valid=False,
                error_message="API key is required",
            )

        if not api_key.startswith("sk-ant-"):
            return KeyValidationResult(
                valid=False,
                error_message="Invalid key format. Anthropic keys start with 'sk-ant-'",
            )

        return None

    async def _call_anthropic_api(self, api_key: str) -> KeyValidationResult:
        """Call Anthropic API to validate key.

        Args:
            api_key: Anthropic API key to validate.

        Returns:
            KeyValidationResult with validation status.
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self.ANTHROPIC_API_BASE}/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                )
                return self._parse_response(response)

        except httpx.TimeoutException:
            return KeyValidationResult(
                valid=False,
                error_message="Unable to reach Anthropic. Check your connection and try again.",
            )
        except httpx.ConnectError:
            return KeyValidationResult(
                valid=False,
                error_message="Unable to connect to Anthropic API. Check your network.",
            )
        except Exception:
            return KeyValidationResult(
                valid=False,
                error_message="Validation failed due to an unexpected error. Please try again.",
            )

    def _parse_response(self, response: httpx.Response) -> KeyValidationResult:
        """Parse Anthropic API response.

        Args:
            response: HTTP response from Anthropic API.

        Returns:
            KeyValidationResult with validation status.
        """
        if response.status_code == 200:
            data = response.json()
            models = [m.get("id", "") for m in data.get("data", [])]
            return KeyValidationResult(
                valid=True,
                models_available=models,
            )

        # Check for known error codes
        error_message = self._ERROR_MESSAGES.get(
            response.status_code,
            f"Unexpected response from Anthropic: {response.status_code}",
        )
        return KeyValidationResult(
            valid=False,
            error_message=error_message,
        )


__all__ = ["AIProviderKeyValidator", "KeyValidationResult"]
