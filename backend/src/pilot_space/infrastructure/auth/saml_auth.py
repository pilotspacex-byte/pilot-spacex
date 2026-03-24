"""SAML 2.0 SP-initiated authentication provider.

Wraps python3-saml (OneLogin) to provide:
  - SP metadata XML generation
  - Login URL construction for IdP redirect binding
  - SAML assertion validation and attribute extraction

This class is synchronous (python3-saml is CPU-bound/sync).
Callers must wrap heavy operations in asyncio.to_thread() if needed in async
contexts, though in practice SAML operations are fast enough for inline use.

SP credentials (entity_id, private key, certificate) are loaded from
application settings at construction time.  IdP configuration (entity_id,
sso_url, certificate) is passed per-request from workspace.settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pilot_space.domain.exceptions import AppError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from fastapi import Request
    from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]

logger = get_logger(__name__)


class SamlValidationError(AppError):
    """Raised when SAML assertion validation fails.

    Covers: missing/invalid signature, expired assertion, audience mismatch,
    replay attacks, and any other validation error from python3-saml.
    """

    http_status: int = 401
    error_code: str = "saml_validation_error"


class SamlAuthProvider:
    """Service Provider SAML operations using python3-saml.

    Args:
        sp_entity_id: SP entity ID URI (e.g. https://app.example.com/saml/metadata).
        sp_private_key_pem: SP private key in PEM format (RSA or ECDSA).
        sp_certificate_pem: SP public certificate in PEM format.

    Note:
        python3-saml expects certificate/key content WITHOUT PEM headers/footers
        in the settings dict.  This class strips headers if present.
    """

    def __init__(
        self,
        sp_entity_id: str,
        sp_private_key_pem: str,
        sp_certificate_pem: str,
    ) -> None:
        self._sp_entity_id = sp_entity_id
        self._sp_private_key = self._strip_pem_headers(sp_private_key_pem)
        self._sp_certificate = self._strip_pem_headers(sp_certificate_pem)

    # ------------------------------------------------------------------
    # Lazy imports (python3-saml excluded on Vercel to stay under 500MB)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_saml_classes() -> tuple[type, type]:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]
        from onelogin.saml2.settings import OneLogin_Saml2_Settings  # type: ignore[import-untyped]

        return OneLogin_Saml2_Auth, OneLogin_Saml2_Settings

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_login_url(
        self,
        request: Request,
        idp_config: dict[str, Any],
        return_to: str,
    ) -> str:
        """Return the IdP redirect-binding SSO URL for SP-initiated login.

        Args:
            request: The incoming FastAPI Request (used to build ACS URL).
            idp_config: Workspace SAML config dict with keys:
                entity_id, sso_url, certificate[, name_id_format].
            return_to: Relay state URL to redirect to after successful login.

        Returns:
            Absolute URL to redirect the user's browser to.

        Raises:
            SamlValidationError: If SAML settings are invalid.
        """
        try:
            SamlAuth, _ = self._get_saml_classes()
            saml_settings = self._build_settings(request, idp_config)
            req = self._prepare_request(request)
            auth = SamlAuth(req, saml_settings)
            return auth.login(return_to=return_to)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning("saml_login_url_failed", error=str(exc))
            raise SamlValidationError(f"Failed to build SAML login URL: {exc}") from exc

    def process_response(
        self,
        request: Request,
        post_data: dict[str, Any],
        idp_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a SAML assertion from the IdP callback.

        Args:
            request: The incoming FastAPI Request (used to build ACS URL).
            post_data: POST form data from the callback, must include SAMLResponse.
            idp_config: Workspace SAML config dict.

        Returns:
            Dict with keys: name_id (str), attributes (dict[str, list]).

        Raises:
            SamlValidationError: If assertion is invalid, expired, has bad
                signature, audience mismatch, or any other validation failure.
        """
        try:
            SamlAuth, _ = self._get_saml_classes()
            saml_settings = self._build_settings(request, idp_config)
            req = self._prepare_request(request, post_data=post_data)
            auth = SamlAuth(req, saml_settings)
            auth.process_response()
        except SamlValidationError:
            raise
        except Exception as exc:
            logger.warning("saml_process_response_error", error=str(exc))
            raise SamlValidationError(f"Error processing SAML response: {exc}") from exc

        self._check_saml_auth_result(auth)

        return {
            "name_id": auth.get_nameid(),
            "attributes": auth.get_attributes(),
        }

    def _check_saml_auth_result(self, auth: OneLogin_Saml2_Auth) -> None:
        """Raise SamlValidationError if the auth object reports errors or is unauthenticated.

        Extracted to a helper to satisfy TRY301 (no raises inside try-except blocks).
        """
        errors = auth.get_errors()
        if errors:
            reason = auth.get_last_error_reason() or str(errors)
            logger.warning("saml_assertion_invalid", errors=errors, reason=reason)
            raise SamlValidationError(f"SAML assertion validation failed: {reason}")

        if not auth.is_authenticated():
            raise SamlValidationError(
                "SAML authentication failed: not authenticated after response processing"
            )

    def get_metadata_xml(self, idp_config: dict[str, Any]) -> bytes:
        """Return the SP metadata XML for this provider.

        Used by IdPs to configure their side of the SAML trust.

        Args:
            idp_config: Workspace SAML config dict (used to build full settings).

        Returns:
            SP metadata XML as bytes.

        Raises:
            SamlValidationError: If metadata generation fails.
        """
        try:
            # Use a minimal fake request to build the settings dict.
            # The ACS URL is the important part of SP metadata.
            from starlette.requests import Request as StarletteRequest
            from starlette.types import Scope

            # Build a minimal ASGI scope so we can construct the ACS URL
            # without a real request object at metadata fetch time.
            fake_scope: Scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/auth/sso/saml/metadata",
                "query_string": b"",
                "headers": [],
                "server": ("localhost", 8000),
                "scheme": "https",
            }
            fake_request = StarletteRequest(fake_scope)

            settings_dict = self._build_settings(fake_request, idp_config)
            _, SamlSettings = self._get_saml_classes()
            settings_obj = SamlSettings(settings=settings_dict, sp_validation_only=True)
            metadata = settings_obj.get_sp_metadata()
            errors = settings_obj.validate_metadata(metadata)
            if errors:
                logger.warning("saml_metadata_validation_errors", errors=errors)
            return metadata if isinstance(metadata, bytes) else metadata.encode()  # type: ignore[union-attr]
        except SamlValidationError:
            raise
        except Exception as exc:
            logger.warning("saml_metadata_generation_failed", error=str(exc))
            raise SamlValidationError(f"Failed to generate SP metadata: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_settings(
        self,
        request: Request,
        idp_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Build python3-saml settings dict from SP config + IdP workspace config.

        Args:
            request: Used to derive the ACS URL base.
            idp_config: Workspace SAML config with entity_id, sso_url, certificate.

        Returns:
            Settings dict accepted by OneLogin_Saml2_Auth.
        """
        acs_url = self._build_acs_url(request)
        idp_cert = self._strip_pem_headers(idp_config.get("certificate", ""))
        name_id_format = idp_config.get(
            "name_id_format",
            "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        )

        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self._sp_entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": name_id_format,
                "x509cert": self._sp_certificate,
                "privateKey": self._sp_private_key,
            },
            "idp": {
                "entityId": idp_config.get("entity_id", ""),
                "singleSignOnService": {
                    "url": str(idp_config.get("sso_url", "")),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": idp_cert,
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": bool(self._sp_private_key),
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": bool(self._sp_certificate),
                "wantMessagesSigned": False,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "wantNameId": True,
                "requestedAuthnContext": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
                "rejectDeprecatedAlgorithm": True,
            },
        }

    def _prepare_request(
        self,
        request: Request,
        post_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert a FastAPI Request to the dict format expected by python3-saml.

        Args:
            request: FastAPI/Starlette Request.
            post_data: POST form data if this is a callback (default empty).

        Returns:
            Dict with keys: https, http_host, script_name, get_data, post_data.
        """
        return {
            "https": "on" if request.url.scheme == "https" else "off",
            "http_host": request.headers.get("host", "localhost"),
            "script_name": request.url.path,
            "get_data": dict(request.query_params),
            "post_data": post_data or {},
        }

    def _build_acs_url(self, request: Request) -> str:
        """Build the Assertion Consumer Service URL from the current request.

        Args:
            request: Used to derive the base URL (scheme + host).

        Returns:
            Absolute ACS URL string.
        """
        base = f"{request.url.scheme}://{request.headers.get('host', 'localhost')}"
        return f"{base}/api/v1/auth/sso/saml/callback"

    @staticmethod
    def _strip_pem_headers(pem: str) -> str:
        """Remove PEM header/footer lines and whitespace from a certificate/key.

        python3-saml settings require the raw base64 content without headers.

        Args:
            pem: PEM-encoded certificate or key (with or without headers).

        Returns:
            Raw base64-encoded content, whitespace stripped.
        """
        lines = pem.strip().splitlines()
        content_lines = [line for line in lines if not line.startswith("-----")]
        return "".join(content_lines).strip()
