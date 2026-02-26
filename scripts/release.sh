#!/usr/bin/env bash
# Pilot Space release script.
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.1.1-alpha.2
set -euo pipefail

# ── Validate args ─────────────────────────────────────────────────────────────
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Error: version argument required" >&2
  echo "Usage: $0 <version>  (e.g. 0.1.1-alpha.2)" >&2
  exit 1
fi

TAG="v${VERSION}"
DATE=$(date +%Y-%m-%d)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
FE_PKG="$REPO_ROOT/frontend/package.json"
BE_TOML="$REPO_ROOT/backend/pyproject.toml"

# Ensure .bak files are cleaned up even on early exit
trap 'rm -f "$CHANGELOG.bak" "$FE_PKG.bak" "$BE_TOML.bak"' EXIT

# ── Validate working tree is clean ────────────────────────────────────────────
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  echo "Error: working tree has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

# ── Validate [Unreleased] has content ─────────────────────────────────────────
UNRELEASED=$(awk '/^## \[Unreleased\]/{found=1; next} found && /^## \[/{exit} found{print}' "$CHANGELOG" | grep -v '^$' || true)
if [[ -z "$UNRELEASED" ]]; then
  echo "Error: [Unreleased] section in CHANGELOG.md is empty. Add entries before releasing." >&2
  exit 1
fi

echo "Releasing $TAG on $DATE..."

# ── Extract [Unreleased] content for GitHub release notes ─────────────────────
RELEASE_NOTES=$(awk '/^## \[Unreleased\]/{found=1; next} found && /^## \[/{exit} found{print}' "$CHANGELOG" || true)

# ── Update CHANGELOG.md ───────────────────────────────────────────────────────
TMP=$(mktemp)
awk -v ver="$VERSION" -v date="$DATE" '
  /^## \[Unreleased\]/ {
    print "## [Unreleased]"
    print ""
    print "## [" ver "] - " date
    next
  }
  { print }
' "$CHANGELOG" > "$TMP" && mv "$TMP" "$CHANGELOG"

# Update the [Unreleased] comparison link at the bottom
sed -i.bak "s|^\[Unreleased\]:.*|\[Unreleased\]: https://github.com/TinDang97/pilot-space/compare/${TAG}...HEAD|" "$CHANGELOG"
# Insert the new version comparison link after [Unreleased] link
PREV_TAG=$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$PREV_TAG" ]]; then
  sed -i.bak "/^\[Unreleased\]:/a\\
[${VERSION}]: https://github.com/TinDang97/pilot-space/compare/${PREV_TAG}...${TAG}" "$CHANGELOG"
fi
rm -f "$CHANGELOG.bak"

# ── Bump frontend/package.json ────────────────────────────────────────────────
if command -v jq &>/dev/null; then
  TMP=$(mktemp)
  jq --arg v "$VERSION" '.version = $v' "$FE_PKG" > "$TMP" && mv "$TMP" "$FE_PKG"
else
  sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$FE_PKG" && rm -f "$FE_PKG.bak"
fi

# ── Bump backend/pyproject.toml ───────────────────────────────────────────────
sed -i.bak "s/^version = \"[^\"]*\"/version = \"$VERSION\"/" "$BE_TOML" && rm -f "$BE_TOML.bak"

# ── Commit + tag ──────────────────────────────────────────────────────────────
git -C "$REPO_ROOT" add CHANGELOG.md frontend/package.json backend/pyproject.toml
git -C "$REPO_ROOT" commit -m "chore(release): $TAG"
git -C "$REPO_ROOT" tag -a "$TAG" -m "Release $TAG"

# ── Push ──────────────────────────────────────────────────────────────────────
git -C "$REPO_ROOT" push
git -C "$REPO_ROOT" push --tags

# ── GitHub Release ────────────────────────────────────────────────────────────
PRERELEASE_ARGS=()
if [[ "$VERSION" == *"-alpha"* ]] || [[ "$VERSION" == *"-beta"* ]] || [[ "$VERSION" == *"-rc"* ]]; then
  PRERELEASE_ARGS=("--prerelease")
fi

gh release create "$TAG" \
  --title "Pilot Space $TAG" \
  --notes "$RELEASE_NOTES" \
  "${PRERELEASE_ARGS[@]}" \
  --repo TinDang97/pilot-space

echo ""
echo "Released $TAG successfully."
