#!/usr/bin/env bash
set -euo pipefail

# Check if version type is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <major|minor|patch>"
    exit 1
fi

VERSION_TYPE=$1

# Validate version type
if [[ ! "$VERSION_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Error: Version type must be 'major', 'minor', or 'patch'"
    exit 1
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Error: Must be on 'main' branch to create a release"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean. Commit or stash changes first."
    exit 1
fi

# Pull latest changes
echo "Pulling latest changes from main..."
git pull origin main

# Update version
echo "Updating version ($VERSION_TYPE)..."
poetry version "$VERSION_TYPE"
NEW_VERSION=$(poetry version -s)

# Update changelog if it exists
if [ -f CHANGELOG.md ]; then
    echo "Updating CHANGELOG.md..."
    DATE=$(date +%Y-%m-%d)
    # Add new version header after the first line
    sed -i '' "2i\\
\\
## [$NEW_VERSION] - $DATE\\
" CHANGELOG.md
    # Open editor for changelog entry
    ${EDITOR:-vi} CHANGELOG.md
fi

# Commit version bump
git add pyproject.toml
if [ -f CHANGELOG.md ]; then
    git add CHANGELOG.md
fi
git commit -m "chore: bump version to $NEW_VERSION"

# Create and push tag
echo "Creating tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

# Push changes
echo "Pushing changes and tags..."
git push origin main
git push origin "v$NEW_VERSION"

echo "Release v$NEW_VERSION created and pushed!"
echo "GitHub Actions will now:"
echo "1. Build and test the code"
echo "2. Build multi-arch Docker images"
echo "3. Push images to GitHub Container Registry"
echo
echo "You can monitor the progress at:"
echo "https://github.com/$GITHUB_REPOSITORY/actions" 