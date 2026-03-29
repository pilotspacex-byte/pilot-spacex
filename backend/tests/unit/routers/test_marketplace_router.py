"""Smoke tests for marketplace router.

Verifies the router is correctly configured with expected endpoints
and validates the route structure.

Source: Phase 054, P54-04
"""

from __future__ import annotations

from pilot_space.api.v1.routers.marketplace import router

PREFIX = "/{workspace_id}/marketplace"


class TestMarketplaceRouterStructure:
    """Verify marketplace router has expected endpoints."""

    def test_router_has_10_routes(self) -> None:
        """Router should have exactly 10 routes."""
        assert len(router.routes) == 10

    def test_router_prefix(self) -> None:
        """Router should have correct prefix."""
        assert router.prefix == PREFIX

    def test_router_tags(self) -> None:
        """Router should have Marketplace tag."""
        assert "Marketplace" in router.tags

    def test_search_listings_route_exists(self) -> None:
        """GET /listings route should exist."""
        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert f"{PREFIX}/listings" in paths

    def test_publish_listing_route_exists(self) -> None:
        """POST /listings route should exist."""
        methods_for_listings = []
        for route in router.routes:
            if hasattr(route, "path") and route.path == f"{PREFIX}/listings":  # type: ignore[union-attr]
                methods_for_listings.extend(route.methods or [])  # type: ignore[union-attr]
        assert "POST" in methods_for_listings

    def test_install_route_exists(self) -> None:
        """POST /listings/{listing_id}/install should exist."""
        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert f"{PREFIX}/listings/{{listing_id}}/install" in paths

    def test_reviews_routes_exist(self) -> None:
        """Review routes should exist."""
        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert f"{PREFIX}/listings/{{listing_id}}/reviews" in paths

    def test_updates_route_exists(self) -> None:
        """GET /updates should exist."""
        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert f"{PREFIX}/updates" in paths

    def test_apply_update_route_exists(self) -> None:
        """POST /installed/{template_id}/update should exist."""
        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert f"{PREFIX}/installed/{{template_id}}/update" in paths
